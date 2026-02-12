import xarray as xr
import rioxarray as rxr
import numpy as np
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import os
from pyproj import CRS, Transformer
import rasterio
import sys


from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders

print("Opening dust dataset...")
location_name = "American Southwest"
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)
dust_df["datetime"] = pd.to_datetime(
    dust_df["Date (YYYYMMDD)"],
    format="%Y%m%d"
)

print("Opening surface usage dataset...")
cec_filepath = (
    "data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif"
)
cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)
src_crs = CRS.from_epsg(4326) 

print("Cropping surface usage raster...")
min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
dst_crs = CRS.from_wkt(cec_full.rio.crs.to_wkt()) 
transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True) 
minx, miny = transformer.transform(min_lon, min_lat) 
maxx, maxy = transformer.transform(max_lon, max_lat) 
minx, maxx = sorted([minx, maxx]) 
miny, maxy = sorted([miny, maxy]) 
cec_cropped = cec_full.rio.clip_box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

output_path = "data/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
if not os.path.exists(output_path):
    print("Reprojecting to lat/lon...") 
    cec = cec_cropped.rio.reproject( 
        "EPSG:4326", 
        resolution=0.05, 
        resampling=rasterio.enums.Resampling.nearest)
    cec.rio.to_raster(output_path)
else:
    print("Processed raster already exists — skipping reprojection.")
    cec = rxr.open_rasterio(output_path).squeeze("band", drop=True)

print("Add usage values to dust dataframe...")
dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

usage_vals = cec.sel(
    x=dust_lons,
    y=dust_lats,
    method="nearest"
).values.squeeze().astype(int) 

dust_df["usage"] = usage_vals

print("Opening data from NARR...")
ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
if ws_data_path.exists():
    print("Opening wind speed dataset...")
    ds_ws = xr.open_dataset(ws_data_path)
else:
    print("Wind speed data not found, exiting...")
    sys.exit()

print("Spatial matching of wind grid...")
def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

lat2d = ds_ws["lat"].values
lon2d = ds_ws["lon"].values

print("Extracting wind speeds at dust events...")
dust_winds = []

for _, row in dust_df.iterrows():
    iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
    
    #--- Day-of time match 
    ws = ds_ws["wind_speed"].sel(
        time=row["datetime"].floor("D"),
        method="nearest"
    ).isel(y=iy, x=ix)
    
    dust_winds.append(ws.compute().item())

dust_df["wind_speed"] = dust_winds
dust_df = dust_df.dropna(subset=["wind_speed"])

print("Binning wind speeds...")
wind_bins = [0, 3, 6, 9, 12, 15, 18, np.inf]
wind_labels = [
    "0-3",
    "3-6",
    "6-9",
    "9-12",
    "12-15",
    "15-18",
    "18+"
]
dust_df["wind_bin"] = pd.cut(
    dust_df["wind_speed"],
    bins=wind_bins,
    labels=wind_labels,
    right=False
)

print("Create dust grouping for heat map...")
combo_counts = (
    dust_df
    .groupby(["wind_bin", "usage"], observed=False)
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
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
combo_counts["usage_name"] = combo_counts["usage"].map(land_cover_dict)
combo_counts["wind_bin"] = combo_counts["wind_bin"].astype(str)

print("(total) Create grouping for heat map...")
usage_df = cec.to_dataframe(name="usage").reset_index()

print("(total) Finding nearest mean wind speed to each usage point...")
print("--- This step is currently slow...")
#--- Requires this method because x and y represent a curvilinear grid
#--- Uses a loop to find the nearest lat lon coords to each texture point
ds_ws_mean = ds_ws.mean(dim="time")
lat = ds_ws_mean.lat.values
lon = ds_ws_mean.lon.values

print("(total) Currently sampling from usage to run faster...")
usage_df = usage_df.sample(n=3000, random_state=33)

def nearest_xy(lat0, lon0):
    dist = (lat - lat0)**2 + (lon - lon0)**2
    return np.unravel_index(dist.argmin(), dist.shape)

indices = [nearest_xy(la, lo) for la, lo in zip(usage_df.y, usage_df.x)]

ws_at_usage = np.array([
    ds_ws_mean['wind_speed'].isel(y=j, x=i).values
    for j, i in indices
])

usage_df["wind_speed"] = ws_at_usage
usage_df["wind_bin"] = pd.cut(
    usage_df["wind_speed"],
    bins=wind_bins,
    labels=wind_labels,
    right=False
)

combo_counts_total = (
    usage_df
    .groupby(["wind_bin", "usage"], observed=False)
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
combo_counts_total["usage_name"] = combo_counts_total["usage"].map(land_cover_dict)
combo_counts_total["wind_bin"] = combo_counts_total["wind_bin"].astype(str)

usage_ref = sorted(combo_counts["usage_name"].dropna().unique())
usage_ref = [t for t in usage_ref if t != 'Other'] + ['Other'] # move 'Other' to end
winds_ref = [w for w in wind_labels
             if w in combo_counts["wind_bin"].values]

print("Plotting difference heat map...")

def compute_wind_usage_matrix(df, usage, winds):
    matrix = df.pivot_table(
        index="wind_bin",
        columns="usage_name",
        values="count",
        aggfunc="sum",
        fill_value=0
    )

    matrix = matrix.reindex(
        index=winds,
        columns=usage,
        fill_value=0
    )

    total = matrix.values.sum()
    matrix = matrix / total
    matrix = matrix.T

    return matrix


def plot_difference_matrix(df1, df2, ax, usage, winds, title):

    m1 = compute_wind_usage_matrix(df1, usage, winds)
    m2 = compute_wind_usage_matrix(df2, usage, winds)

    diff = m1 - m2

    vmax = np.max(np.abs(diff.values))

    im = ax.imshow(
        diff.values,
        vmin=-vmax,
        vmax=vmax,
        cmap="seismic",  # diverging colormap
        aspect="auto"
    )

    ax.set_xlabel("Wind speed (m/s)", size=15)
    ax.set_xticks(np.arange(diff.shape[1]))
    ax.set_yticks(np.arange(diff.shape[0]))
    ax.set_xticklabels(diff.columns, size=12)
    ax.set_yticklabels(diff.index, size=12)

    ax.set_title(title, size=18)

    norm = im.norm
    for i in range(diff.shape[0]):
        for j in range(diff.shape[1]):
            val = diff.values[i, j]
            if val != 0:
                text_color = "white" if (val*100) < -8 else "black"

                ax.text(
                    j, i,
                    f"{val*100:.2f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color
                )

    return im

# ---- Plot ----

fig, ax = plt.subplots(figsize=(7, 6))

im_diff = plot_difference_matrix(
    combo_counts,
    combo_counts_total,
    ax,
    usage_ref,
    winds_ref,
    "Likelihood of wind speed causing dust \n in surface usage domains"
)

fig.colorbar(im_diff, ax=ax, label="Above-mean difference (%)")

plt.savefig(
    os.path.join("figures", "winds_usage_heatmap"),
    bbox_inches='tight',
    dpi=300
)