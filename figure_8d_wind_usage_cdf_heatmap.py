from pathlib import Path
import xarray as xr
import sys
import rioxarray as rxr
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as soil_orders


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

print("Getting usage names and choosing which to plot...")
selected_usages = [7, 15, 8, 16, 10]
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
dust_df_filtered = dust_df[dust_df["usage"].isin(selected_usages)]

print("Building and plotting the cumulative distribution function...")
#freq of dust = blowing per domain / domain count 
dust_df_sorted = dust_df_filtered.sort_values(['usage', 'wind_speed'])
dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('usage').cumcount() + 1
dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('usage')['cum_pct'].transform('max') * 100


wind_bins = list(range(0, 16))
wind_bins.append(np.inf)

dust_df_sorted['wind_bin'] = pd.cut(
    dust_df_sorted['wind_speed'],
    bins=wind_bins,
    right=False
)

heatmap_data = dust_df_sorted.pivot_table(
    index='usage',
    columns='wind_bin',
    values='cum_pct',
    aggfunc='mean',
    fill_value=0, 
    observed=False  
)

fig, ax = plt.subplots(figsize=(9, 4))

im = ax.imshow(
    heatmap_data.values, 
    aspect='auto', 
    cmap='binary',
    origin='lower',
    vmax=100
)

ax.set_yticks(np.arange(heatmap_data.shape[0]))
ax.set_yticklabels([land_cover_dict[u] for u in heatmap_data.index])

ax.set_xlabel('Wind Speed (m/s)', size=15)
ax.set_title('Dust events by wind speed and \n land usage category', size=18)

cbar = fig.colorbar(im, ax=ax)
cbar.set_label('Cumulative Percentage', size=15)
cbar.ax.tick_params(labelsize=12)

plt.tight_layout()

soil_orders._plot_save(
    fig,
    plot_dir="figures",
    plot_name="wind_usage_cdf_heatmap"
)
