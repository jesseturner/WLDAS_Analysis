import rioxarray as rxr
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np

from modules_line_dust import line_dust_utils as dust
from modules_texture import gldas_texture_utils as gldas
from modules_soil_orders import soil_orders_utils as orders

location_name = "American Southwest"

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)

#--- Get soil texture data
gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
texture_da = texture_ds.GLDAS_soiltex

#--- Get soil order data
usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
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

#--- Ensure consistent coordinate names
texture = texture_da.rename({"lat": "y", "lon": "x"})
soil = soil_da.rename({"y": "y", "x": "x"})

#--- Create DataArrays of dust coordinates
dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

#--- Sample nearest grid cell
texture_vals = texture.sel(
    x=dust_lons,
    y=dust_lats,
    method="nearest"
).values.squeeze().astype(int) 

soil_vals = soil.sel(
    x=dust_lons,
    y=dust_lats,
    method="nearest"
).values

#--- Attach to DataFrame
dust_df["texture"] = texture_vals
dust_df["soil"] = soil_vals

#--- Count combinations
combo_counts = (
    dust_df
    .groupby(["soil", "texture"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
top15 = combo_counts.head(15).copy()
print(top15)

#--- Labels for plotting
top15["label"] = (
    "Soil=" + top15["soil"].astype(str)
    + ", Texture=" + top15["texture"].astype(str)
)

soil_order_dict = orders._get_soil_order_dict()

#--- Plot bar chart
fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(top15["label"], top15["count"])

ax.set_xlabel("Soil / Texture Combination")
ax.set_ylabel("Number of Dust Points")
ax.set_title("Top 15 Most Frequent Soil-Texture Combinations")
plt.xticks(rotation=45, ha="right")

plt.tight_layout()
orders._plot_save(fig, plot_dir="figures", plot_name="inherent_combo")

