from pathlib import Path
import xarray as xr
import sys
import rioxarray as rxr
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders
from modules_texture import gldas_texture_utils as gldas

def main():
    #--- WIND SPEED DATA
    ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
    if ws_data_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(ws_data_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()

    #--- DUST DATA
    print("Opening dust dataset...")
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name=location_name)
    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"],
        format="%Y%m%d"
    )

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

    print("---DATAFRAME COMPLETE---")

    dust_df_sorted, column_name, selected_list, colors, save_name = usage_info_for_cdf(dust_df)
    plot_cdf(dust_df_sorted, column_name, selected_list, colors, save_name)

    dust_df_sorted, column_name, selected_list, colors, save_name = soil_order_info_for_cdf(dust_df)
    plot_cdf(dust_df_sorted, column_name, selected_list, colors, save_name)

    dust_df_sorted, column_name, selected_list, colors, save_name = texture_info_for_cdf(dust_df)
    plot_cdf(dust_df_sorted, column_name, selected_list, colors, save_name)

    return

#------------------------

def plot_cdf(dust_df_sorted, column_name, selected_list, colors, save_name):

    fig, ax = plt.subplots(figsize=(15, 6))

    for i, category in enumerate(selected_list):
        subset = dust_df_sorted[dust_df_sorted[column_name] == category]
        ax.step(subset['wind_speed'], subset['cum_pct'], where='post', 
                label=selected_list[i],
                color=colors[i], 
                linewidth=3)

    ax.set_xlim(0, 20)
    ax.set_xlabel('Wind Speed (m/s)', size=15)
    ax.set_ylabel('Cumulative Percentage (%)', size=15)
    ax.set_title('Dust events by wind speed and category', size=18)
    ax.tick_params(axis='both', which='major', labelsize=15) 
    ax.legend(fontsize=15)

    plt.tight_layout()
    plt.savefig(os.path.join("figures", save_name), bbox_inches='tight', dpi=300)
    plt.close(fig)
    return

def usage_info_for_cdf(dust_df):
    print("Getting usage names and choosing which to plot...")
    # selected_usages = [7, 15, 8, 16, 10]
    selected_usages = ["Tropical/Sub-tropical Shrubland", "Cropland", "Temp/Sub-polar Shrubland", "Barren Lands", "Temp/Sub-polar Grassland"]
    land_cover_dict = {
        1: "Temp/Sub-polar Needleleaf Forest",
        2: "Sub-polar Taiga Needleleaf Forest",
        3: "Tropical Broadleaf Evergreen Forest",
        4: "Tropical Broadleaf Deciduous Forest",
        5: "Temp/Sub-polar Broadleaf Deciduous Forest",
        6: "Mixed Forest",
        7: "Tropical/Sub-tropical Shrubland",
        8: "Temp/Sub-polar Shrubland",
        9: "Tropical/Sub-tropical Grassland",
        10: "Temp/Sub-polar Grassland",
        11: "Sub-polar Shrub-Lichen-Moss",
        12: "Sub-polar Grass-Lichen-Moss",
        13: "Sub-polar Barren-Lichen-Moss",
        14: "Wetland",
        15: "Cropland",
        16: "Barren Lands",
        17: "Urban and Built-up",
        18: "Water",
        19: "Snow and Ice",
    } 
    dust_df["usage_name"] = dust_df["usage"].map(land_cover_dict)
    dust_df_filtered = dust_df[dust_df["usage_name"].isin(selected_usages)]
    colors = [
        "#7a554f", #Tropical/Sub-tropical Shrubland
        "#e7cd24", #Cropland
        "#a28073", #Temp/Sub-polar Shrubland
        "#F60707", #Barren Lands
        "#9db72b", #Temp/Sub-polar Grassland
    ]
    save_name = "wind_usage_cdf.png"
    column_name = "usage_name"

    print("Building and plotting the usage cumulative distribution function...")
    #freq of dust = blowing per domain / domain count 
    dust_df_sorted = dust_df_filtered.sort_values(['usage_name', 'wind_speed'])
    dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('usage_name').cumcount() + 1
    dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('usage_name')['cum_pct'].transform('max') * 100

    return dust_df_sorted, column_name, selected_usages, colors, save_name

def soil_order_info_for_cdf(dust_df):
    print("Getting soil order names and choosing which to plot...")
    order_dict = orders.get_soil_order_dict()
    dust_df["soil_order_name"] = dust_df["soil_order"].map(order_dict)
    selected_soil_orders = ['Aridisols', 'Entisols', 'Mollisols', 'Alfisols', 'Shifting Sands']
    dust_df_filtered = dust_df[dust_df["soil_order_name"].isin(selected_soil_orders)]

    colors = [
        "#f1af4c", #Aridisols
        "#dc5908", #Entisols
        "#046a2b", #Mollisols
        "#06dd0a", #Alfisols
        "#a8a6a4" #Shifting Sands
    ]
    save_name = "wind_order_cdf.png"
    column_name = "soil_order_name"
    
    print("Building and plotting the order cumulative distribution function...")
    #freq of dust = blowing per domain / domain count
    dust_df_sorted = dust_df_filtered.sort_values(['soil_order_name', 'wind_speed'])
    dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('soil_order_name').cumcount() + 1
    dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('soil_order_name')['cum_pct'].transform('max') * 100

    return dust_df_sorted, column_name, selected_soil_orders, colors, save_name

def texture_info_for_cdf(dust_df):
    print("Getting texture names and choosing which to plot...")
    texture_dict = gldas.get_texture_dict()
    dust_df["texture_name"] = dust_df["texture"].map(texture_dict)
    selected_texture_orders = ['Sand', 'Sandy Loam', 'Loam', 'Sandy Clay Loam', 'Silty Clay', 'Clay']
    dust_df_filtered = dust_df[dust_df["texture_name"].isin(selected_texture_orders)]

    colors = [
        "#EE6352",  # Sand
        "#d9c070",  # Sandy Loam
        "#a67c52",  # Loam
        "#16DB93",  # Sandy Clay Loam
        "#048BA8",  # Silty Clay
        "#4f1f18",  # Clay
    ]
    save_name = "wind_texture_cdf.png"
    column_name = "texture_name"
    
    print("Building and plotting the order cumulative distribution function...")
    #freq of dust = blowing per domain / domain count
    dust_df_sorted = dust_df_filtered.sort_values(['texture_name', 'wind_speed'])
    dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('texture_name').cumcount() + 1
    dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('texture_name')['cum_pct'].transform('max') * 100

    return dust_df_sorted, column_name, selected_texture_orders, colors, save_name





#------------------------

if __name__ == "__main__":
    main()