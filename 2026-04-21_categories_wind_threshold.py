from pathlib import Path
import xarray as xr
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import rioxarray as rxr
import sys
from matplotlib.patches import Patch

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders
from modules_texture import gldas_texture_utils as gldas

def main():
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    #--- wind data
    processed_wind_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
    dust_df = add_winds_to_dust_df(processed_wind_path, dust_df)

    #--- category data
    dust_df = add_static_data(dust_df, location_name)

    #--- create non-dust dataframe
    non_dust_df = create_non_dust_grid(dust_df)
    non_dust_df_sample = non_dust_df.sample(n=1_000, random_state=9)
    non_dust_df_sample = add_winds_to_dust_df(processed_wind_path, non_dust_df_sample)
    non_dust_df_sample = add_static_data(non_dust_df_sample, location_name)

    print(dust_df)
    print(non_dust_df_sample)

    plot_bar_soil_texture(dust_df, non_dust_df_sample)


#------------------------

def get_dust_df(dust_path):
    print("Opening dust data, creating dust dataframe... ")
    dust_df = dust.read_dust_data_into_df(dust_path)

    dust_df["time_str"] = (
        dust_df["start time (UTC)"]
        .astype("Int64")        # allows NaNs safely
        .astype(str)
        .str.zfill(4)
    )

    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"].astype(str) + dust_df["time_str"],
        format="%Y%m%d%H%M",
        utc=True,
        errors="coerce"
    )

    n_before = len(dust_df)
    dust_df = dust_df.dropna(subset=["datetime"]).copy()
    n_after = len(dust_df)
    n_removed = n_before - n_after
    print(f"Removed {n_removed} dust events due to invalid datetime parsing.")

    dust_df["datetime"] = (
        dust_df["datetime"]
        .dt.tz_convert(None)
    )
    return dust_df

def add_winds_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")

    def nearest_grid_point(lat2d, lon2d, lat, lon):
        dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
        iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
        return iy, ix
    lat2d = ds_ws["lat"].values
    lon2d = ds_ws["lon"].values

    dust_winds = []
    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        
        #--- Day-of time match 
        ws = ds_ws["wind_speed"].sel(
            time=row["datetime"].floor("D"),
            method="nearest"
        ).isel(y=iy, x=ix)
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds
    dust_df = dust_df.dropna(subset=["wind_speed"])

    return dust_df

def add_static_data(dust_df, location_name):
    #--- USAGE DATA
    cover_data_path = "data/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
    if os.path.exists(cover_data_path):
        print("Opening surface usage dataset...")
        usage = rxr.open_rasterio(cover_data_path).squeeze("band", drop=True)
    else:
        print("Land cover data not found, exiting...")
        
    print("For each dust event, getting the usage...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

    usage_vals = usage.sel(
        x=dust_lons,
        y=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 

    dust_df["usage"] = usage_vals

    #--- TEXTURE DATA
    print("Opening soil texture dataset...")
    gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
    texture_ds = gldas.open_gldas_file(gldas_path)
    texture_ds = gldas.filter_to_region(texture_ds, location_name)
    texture_da = texture_ds.GLDAS_soiltex

    print("Add texture values to dust dataframe...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")
    texture_vals = texture_da.sel(
        lon=dust_lons,
        lat=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 
    dust_df["texture"] = texture_vals

    #--- SOIL ORDERS DATA
    print("Opening soil orders dataset...")
    usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
    location_name="American Southwest"
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    soil_da = (
        rxr.open_rasterio(usda_filepath)
        .squeeze("band", drop=True)
        .rio.clip_box(
            minx=min_lon,
            miny=min_lat,
            maxx=max_lon,
            maxy=max_lat,
        )
    )

    print("Add soil order values to dust dataframe...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")
    soil_vals = soil_da.sel(
        x=dust_lons,
        y=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 
    dust_df["soil_order"] = soil_vals

    return dust_df

def create_non_dust_df(dust_df):
    '''
    Create dataframe of dust source locations when they are not actively blowing dust in 2001-2020. 
    '''
    print("Creating the non-dust dataframe...")

    lat_lon = dust_df[["latitude", "longitude"]].drop_duplicates()
    dates = pd.date_range(start="2001-01-01", end="2020-12-31", freq="D")
    dust_dates = pd.to_datetime(dust_df["datetime"]).dt.normalize().unique()
    filtered_dates = dates[~dates.isin(dust_dates)]
    dates_df = pd.DataFrame({"date": filtered_dates})
    non_dust_df = lat_lon.merge(dates_df, how="cross")
    non_dust_df["datetime"] = pd.to_datetime(non_dust_df["date"])
    non_dust_df = non_dust_df.drop(columns="date")

    print(f"Non-dust dataframe: {np.shape(non_dust_df)}, from {len(filtered_dates)} non-dust days...")

    return non_dust_df

def create_non_dust_grid(dust_df):
    '''
    Create dataframe of full domain grid in 2001-2020. 
    '''
    print("Creating the non-dust dataframe...")

    #--- Creating standard cube
    lats = np.arange(28, 46, 3)
    lons = np.arange(-128, -98, 3)
    dates = pd.date_range("2001-01-01 18:00:00", 
                      "2020-12-31 18:00:00", 
                      freq="D")
    grid = pd.MultiIndex.from_product(
        [dates, lats, lons],
        names=["datetime", "latitude", "longitude"]
    ).to_frame(index=False)

    print(f"Standard grid created of shape ({len(lons)},{len(lats)},{len(dates)})...")

    #--- Remove dust points
    print("Removing dust points from grid...")

    dust_df["date"] = dust_df["datetime"].dt.date
    grid["date"] = grid["datetime"].dt.date

    #--- Filtering to remove dust points (by day) within 2 degrees
    dist_to_remove = 2

    merged = grid.merge(
        dust_df,
        on="date",
        how="left",
        suffixes=("_grid", "_dust"))

    # Create condition: close in both lat & lon
    mask = (
        (abs(merged["latitude_grid"] - merged["latitude_dust"]) <= dist_to_remove) &
        (abs(merged["longitude_grid"] - merged["longitude_dust"]) <= dist_to_remove)
    )

    # Flag rows that should be removed
    merged["remove"] = mask

    # Collapse back to grid level
    to_remove = merged.groupby(
        ["date", "latitude_grid", "longitude_grid"]
    )["remove"].any().reset_index()

    # Keep only rows NOT marked for removal
    grid_filtered = to_remove[~to_remove["remove"]]

    # Clean up column names
    grid_filtered = grid_filtered.rename(columns={
        "latitude_grid": "latitude",
        "longitude_grid": "longitude"
    }).drop(columns="remove")

    print(f"---> {grid.shape[0]} reduced to {grid_filtered.shape[0]}")
    non_dust_df = grid_filtered

    #--- Add datetime, set to 1800 UTC
    non_dust_df["datetime"] = pd.to_datetime(non_dust_df["date"]) + pd.Timedelta(hours=18)

    return non_dust_df

def plot_bar_soil_texture(dust_df, non_dust_df):
    """
    Create a side-by-side bar chart comparing:
    - frequency of soil textures at dust points
    - frequency of soil textures in the full soil raster
    """

    texture_dict = gldas.get_texture_dict()

    #--- Calculate bins
    dust_counts = {k: np.sum(dust_df['texture'] == k) for k in texture_dict.keys()}
    dust_total = sum(dust_counts.values())
    dust_fraction = {k: v / dust_total for k, v in dust_counts.items()}

    non_dust_counts = {k: np.sum(non_dust_df['texture'] == k) for k in texture_dict.keys()}
    non_dust_total = sum(non_dust_counts.values())
    non_dust_fraction = {k: v / non_dust_total for k, v in non_dust_counts.items()}

    texture_colors = [
        "#EE6352",  # Sand
        "#e6d591",  # Loamy Sand
        "#d9c070",  # Sandy Loam
        "#c0b080",  # Silt Loam
        "#b0a070",  # Silt
        "#a67c52",  # Loam
        "#16DB93",  # Sandy Clay Loam
        "#9c6644",  # Silty Clay Loam
        "#805533",  # Clay Loam
        "#8c3f2f",  # Sandy Clay
        "#048BA8",  # Silty Clay
        "#4f1f18",  # Clay
        "#1a1a1a",  # Organic Matter
        "#3399ff",  # Water
        "#808080",  # Bedrock
        "#ffffff",  # Other
    ]

    # Prepare for plotting
    categories = list(texture_dict.keys())
    labels = [texture_dict[k] for k in categories]
    x = np.arange(len(categories))
    width = 0.4

    fig, ax = plt.subplots(figsize=(16, 8))

    # Plot bars
    for i, k in enumerate(categories):
        color = texture_colors[i]
        ax.bar(x[i] - width / 2, dust_fraction[k], width, color=color, edgecolor="black", label="Dust points" if i == 0 else "")
        ax.bar(x[i] + width / 2, non_dust_fraction[k], width, color=color, alpha=0.5, label="Full domain" if i == 0 else "")

    # Labels and ticks
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Fraction of observations")
    ax.set_xlabel("Soil Texture")
    ax.set_title(f"Soil Texture Frequency in American Southwest: Dust ")

    # Legend
    legend_elements = [
        Patch(facecolor="gray", edgecolor="black", label="Dust points"),
        Patch(facecolor="gray", edgecolor="black", alpha=0.5, label="Full domain")
    ]
    ax.legend(handles=legend_elements, title="Dataset")

    plt.tight_layout()
    plt.savefig(os.path.join("figures", "texture_bar_chart_threshold"), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

#------------------------

if __name__ == "__main__":
    main()