import rioxarray as rxr
from pyproj import CRS, Transformer
import rasterio
import os
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import textwrap

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders

location_name = "American Southwest"

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)

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

#--- Get surface usage data
cec_filepath = (
    "data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif"
)

print("Opening file...") 
cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)
src_crs = CRS.from_epsg(4326) 

print("Cropping raster...")
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

#--- Ensure consistent coordinate names
usage = cec.rename({"y": "y", "x": "x"})
soil = soil_da.rename({"y": "y", "x": "x"})

#--- Create DataArrays of dust coordinates
dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

#--- Sample nearest grid cell
usage_vals = usage.sel(
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
dust_df["usage"] = usage_vals
dust_df["soil"] = soil_vals

#--- Count combinations
combo_counts = (
    dust_df
    .groupby(["soil", "usage"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

#--- Count combinations total
usage_df = usage.to_dataframe(name="usage").reset_index()

soil_at_usage = soil_da.sel(
    x=xr.DataArray(usage_df["x"].values, dims="points"),
    y=xr.DataArray(usage_df["y"].values, dims="points"),
    method="nearest"
).values

usage_df["soil"] = soil_at_usage
usage_df = usage_df[usage_df["soil"] != soil_da._FillValue]

combo_counts_total = (
    usage_df
    .groupby(["soil", "usage"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

#--- Map to category names
soil_order_dict = orders.get_soil_order_dict()
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
combo_counts["soil_name"] = combo_counts["soil"].map(soil_order_dict)
combo_counts_total["usage_name"] = combo_counts_total["usage"].map(land_cover_dict)
combo_counts_total["soil_name"] = combo_counts_total["soil"].map(soil_order_dict)

#--- Plot heatmap
def plot_soil_texture_matrix(df, ax, textures, soils, title):
    matrix = df.pivot_table(
        index="soil_name",
        columns="usage_name",
        values="count",
        aggfunc="sum",
        fill_value=0
    )

    matrix = matrix.reindex(
        index=soils,
        columns=textures,
        fill_value=0
    )

    total = matrix.values.sum()
    matrix = matrix / total

    vmax = np.max(matrix.values)

    im = ax.imshow(
        matrix.values,
        vmin=0,
        vmax=vmax,
        cmap="binary"
    )

    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_yticks(np.arange(matrix.shape[0]))

    wrapped_labels = [textwrap.fill(label, width=24) for label in matrix.columns]
    ax.set_xticklabels(wrapped_labels, rotation=60, ha="right", size=12)
    ax.set_yticklabels(matrix.index, size=15)
    ax.set_title(title, size=18)

    # Cell labels (formatted as fraction or %)
    norm = im.norm
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix.values[i, j]
            if val > 0:
                text_color = "white" if norm(val) > 0.5 else "black"

                ax.text(
                    j, i, f"{(val*100):.2f}",   # percent formatting
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color
                )

    return im

fig, axes = plt.subplots(
    nrows=1,
    ncols=2,
    figsize=(15, 12),
    sharey=True,
    constrained_layout=True)

usage_ref = sorted(combo_counts["usage_name"].dropna().unique())
soils_ref = sorted(combo_counts["soil_name"].dropna().unique())
im1 = plot_soil_texture_matrix(combo_counts, axes[0], usage_ref, soils_ref, "Dust events")
im2 = plot_soil_texture_matrix(combo_counts_total, axes[1], usage_ref, soils_ref, "Full domain")

plt.savefig(os.path.join("figures", "soil_usage_heatmap"), bbox_inches='tight', dpi=300)