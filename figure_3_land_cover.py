import numpy as np
import xarray as xr
import rioxarray as rxr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import rasterio
from pyproj import CRS, Transformer
import os
import pandas as pd

from modules_soil_orders import soil_orders_utils as soil_orders
from modules_line_dust import line_dust_utils as dust


# --------------------------------------------------
# Paths + region bounds
# --------------------------------------------------
cec_filepath = (
    "data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/"
    "NA_NALCMS_landcover_2020v2_30m.tif"
)

min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region(
    "American Southwest"
)
#--- Adjust for reprojection
min_lat_extend = min_lat - 5
max_lat_extend = max_lat + 4


# --------------------------------------------------
# Open → clip → reproject 
# --------------------------------------------------
print("Opening file...") 
cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)

print("Cropping raster...")
src_crs = CRS.from_epsg(4326) 
dst_crs = CRS.from_wkt(cec_full.rio.crs.to_wkt()) 
transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True) 
minx, miny = transformer.transform(min_lon, min_lat_extend) 
maxx, maxy = transformer.transform(max_lon, max_lat_extend) 
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

# --------------------------------------------------
# Land cover classes
# --------------------------------------------------
classes = {
    1: ("Temp/Sub-polar Needleleaf Forest", "#1b5e20"),
    2: ("Sub-polar Taiga Needleleaf Forest", "#2e7d32"),
    3: ("Tropical Broadleaf Evergreen Forest", "#388e3c"),
    4: ("Tropical Broadleaf Deciduous Forest", "#66bb6a"),
    5: ("Temp/Sub-polar Broadleaf Deciduous Forest", "#81c784"),
    6: ("Mixed Forest", "#4caf50"),
    7: ("Tropical/Sub-tropical Shrubland", "#a1887f"),
    8: ("Temp/Sub-polar Shrubland", "#8d6e63"),
    9: ("Tropical/Sub-tropical Grassland", "#dce775"),
    10: ("Temp/Sub-polar Grassland", "#c0ca33"),
    11: ("Sub-polar Shrub–Lichen–Moss", "#b0bec5"),
    12: ("Sub-polar Grass–Lichen–Moss", "#90a4ae"),
    13: ("Sub-polar Barren–Lichen–Moss", "#78909c"),
    14: ("Wetland", "#26c6da"),
    15: ("Cropland", "#ffeb3b"),
    16: ("Barren Lands", "#bcaaa4"),
    17: ("Urban and Built-up", "#e53935"),
    18: ("Water", "#1e88e5"),
    19: ("Snow and Ice", "#e0f7fa"),
}

codes = np.array(sorted(classes))
names = [classes[c][0] for c in codes]
colors = [classes[c][1] for c in codes]

cmap = mcolors.ListedColormap(colors)
cec = cec.where(np.isin(cec, codes)) #--- Null values are not included
norm = mcolors.BoundaryNorm(
    boundaries=np.append(codes - 0.5, codes[-1] + 0.5),
    ncolors=len(colors),
)


# --------------------------------------------------
# Plot
# --------------------------------------------------
print("Plotting...")
fig, ax = plt.subplots(
    figsize=(16, 12),
    subplot_kw={"projection": ccrs.PlateCarree()},
)

cec.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap=cmap,
    norm=norm,
    add_colorbar=False,
)

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

#--- Plot dust points
ax.scatter(
    dust_df["longitude"],
    dust_df["latitude"],
    transform=ccrs.PlateCarree(),
    s=12,
    marker="o",
    facecolors='white',
    edgecolors='black',
    linewidth=1, 
    alpha=1,
    zorder=2
)

ax.set_title("Land Cover Categories with Dust Origins")

ax.add_feature(cfeature.STATES, linewidth=0.8)
ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=4)
ax.add_feature(cfeature.BORDERS, linewidth=0.8)
ax.add_feature(cfeature.OCEAN, facecolor='white', zorder=3)
ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

legend_handles = [
    mpatches.Patch(color=color, label=name)
    for name, color in zip(names, colors)
]

ax.legend(
    handles=legend_handles,
    title="Land Cover Class",
    loc="center left",
    bbox_to_anchor=(1.02, 0.5),
    frameon=True,
)

plt.tight_layout()
soil_orders._plot_save(fig, plot_dir="figures", plot_name="cec_land_cover")

# --------------------------------------------------
# Sample land cover at dust point locations
# --------------------------------------------------
print("Plotting bar chart...")
dust_da = xr.DataArray(
    dust_df[["latitude", "longitude"]].values,
    dims=("points", "coords"),
    coords={"coords": ["y", "x"]},
)

dust_lc = cec.sel(
    x=dust_da.sel(coords="x"),
    y=dust_da.sel(coords="y"),
    method="nearest"
)

dust_codes = dust_lc.values.astype("float")
dust_codes = dust_codes[~np.isnan(dust_codes)].astype(int)

# --------------------------------------------------
# Frequency counts
# --------------------------------------------------
full_codes = cec.values.flatten()
full_codes = full_codes[~np.isnan(full_codes)].astype(int)

dust_counts = pd.Series(dust_codes).value_counts()
full_counts = pd.Series(full_codes).value_counts()

counts_df = pd.DataFrame({
    "Dust points": dust_counts,
    "Full domain": full_counts
}).fillna(0)

# Normalize to fractions
counts_df = counts_df.div(counts_df.sum())

# Map code → name
counts_df.index = counts_df.index.map(lambda c: classes[c][0])

# Sort by dust contribution
counts_df = counts_df.sort_values("Dust points", ascending=False)

# --------------------------------------------------
# Bar chart
# --------------------------------------------------
fig_bar, ax_bar = plt.subplots(figsize=(12, 6))

x = np.arange(len(counts_df))
width = 0.35

for i, lc_name in enumerate(counts_df.index):
    # recover class code
    lc_code = [k for k, v in classes.items() if v[0] == lc_name][0]
    color = cmap(codes.tolist().index(lc_code))

    ax_bar.bar(
        x[i] - width / 2,
        counts_df.loc[lc_name, "Dust points"],
        width,
        color=color,
        edgecolor="black",
        linewidth=1,
        label="Dust points" if i == 0 else ""
    )

    ax_bar.bar(
        x[i] + width / 2,
        counts_df.loc[lc_name, "Full domain"],
        width,
        color=color,
        alpha=0.5,
        label="Full domain" if i == 0 else ""
    )

ax_bar.set_xticks(x)
ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
ax_bar.set_ylabel("Fraction of total")
ax_bar.set_title("Land Cover Distribution: Dust Points vs Full Domain")

ax_bar.legend()
plt.tight_layout()

soil_orders._plot_save(fig_bar, plot_dir="figures", plot_name="cec_land_cover_bar_chart")
