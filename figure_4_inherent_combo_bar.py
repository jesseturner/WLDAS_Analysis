import rioxarray as rxr
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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

#--- Count combinations total
texture2d = texture_da.isel(time=0)
texture_df = texture2d.to_dataframe(name="texture").reset_index()
texture_df["texture"] = texture_df["texture"].fillna(0).astype(int)

soil_at_texture = soil_da.sel(
    x=xr.DataArray(texture_df["lon"].values, dims="points"),
    y=xr.DataArray(texture_df["lat"].values, dims="points"),
    method="nearest"
).values

texture_df["soil"] = soil_at_texture
texture_df = texture_df[texture_df["soil"] != soil_da._FillValue]

combo_counts_total = (
    texture_df
    .groupby(["soil", "texture"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
top15_total = combo_counts_total.head(15).copy()

#--- Map to category names
soil_order_dict = orders._get_soil_order_dict()
texture_dict = gldas.get_texture_dict()

top15["texture_name"] = top15["texture"].map(texture_dict)
top15["soil_name"] = top15["soil"].map(soil_order_dict)

top15["texture_name"] = top15["texture_name"].fillna(
    "Unknown texture (" + top15["texture"].astype(str) + ")"
)
top15["soil_name"] = top15["soil_name"].fillna(
    "Unknown soil (" + top15["soil"].astype(str) + ")"
)

top15_total["texture_name"] = top15_total["texture"].map(texture_dict)
top15_total["soil_name"] = top15_total["soil"].map(soil_order_dict)

top15_total["texture_name"] = top15_total["texture_name"].fillna(
    "Unknown texture (" + top15_total["texture"].astype(str) + ")"
)
top15_total["soil_name"] = top15_total["soil_name"].fillna(
    "Unknown soil (" + top15_total["soil"].astype(str) + ")"
)

#--- Create plot labels
top15["label"] = (
    top15["soil_name"]
    + " | "
    + top15["texture_name"]
)

top15_total["label"] = (
    top15_total["soil_name"]
    + " | "
    + top15_total["texture_name"]
)

#--- Create merged labeling
count_dust = top15[["label", "count"]].rename(columns={"count": "dust_count"})
count_total = top15_total[["label", "count"]].rename(columns={"count": "total_count"})

combo_plot = (
    count_dust
    .merge(count_total, on="label", how="outer")
    .fillna(0)
)
combo_plot = combo_plot.sort_values(
    ["dust_count", "total_count"],
    ascending=False
)
combo_plot = combo_plot.reset_index(drop=True)

#--- Plot bar chart
x = np.arange(len(combo_plot))
width = 0.4

fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(
    x - width / 2,
    combo_plot["dust_count"],
    width,
    color="tab:orange",
    edgecolor="black",
    linewidth=1,
    label="Dust events"
)

ax.bar(
    x + width / 2,
    combo_plot["total_count"],
    width,
    color="tab:blue",
    alpha=0.5,
    label="Full domain"
)

ax.set_xlabel("Soil | Texture Combination")
ax.set_ylabel("Count")
ax.set_title("Top Soil-Texture Combinations\n(Dust vs Total Domain)")
ax.set_xticks(x)
ax.set_xticklabels(combo_plot["label"], rotation=45, ha="right")
ax.legend()


plt.tight_layout()
orders._plot_save(fig, plot_dir="figures", plot_name="inherent_combo")

