import numpy as np
import xarray as xr
import rioxarray as rxr
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from pyproj import CRS, Transformer
import rasterio

from modules_soil_orders import soil_orders_utils as soil_orders


# --------------------------------------------------
# File path + region bounds
# --------------------------------------------------
cec_filepath = "data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif"

min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region("American Southwest")


# --------------------------------------------------
# Open the GeoTIFF
# --------------------------------------------------
print("Opening file...")
cec_da = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)


# --------------------------------------------------
# Crop to lat/lon range
# --------------------------------------------------
print("Cropping to American Southwest...")

src_crs = CRS.from_epsg(4326)
dst_crs = CRS.from_wkt(cec_da.rio.crs.to_wkt())

transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True)

minx, miny = transformer.transform(min_lon, min_lat)
maxx, maxy = transformer.transform(max_lon, max_lat)

minx, maxx = sorted([minx, maxx])
miny, maxy = sorted([miny, maxy])

cec_clip = cec_da.rio.clip_box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)


# --------------------------------------------------
# Land cover class definitions
# --------------------------------------------------
class_colors = {
    1: {"name": "Temp/Sub-polar Needleleaf Forest", "codes": [20134], "color": "#1b5e20"},
    2: {"name": "Sub-polar Taiga Needleleaf Forest", "codes": [20229], "color": "#2e7d32"},
    3: {"name": "Tropical Broadleaf Evergreen Forest", "codes": [20090], "color": "#388e3c"},
    4: {"name": "Tropical Broadleaf Deciduous Forest", "codes": [20132], "color": "#66bb6a"},
    5: {"name": "Temp/Sub-polar Broadleaf Deciduous Forest", "codes": [20227], "color": "#81c784"},
    6: {"name": "Mixed Forest", "codes": [20092, 20090, 20134, 20132, 20229, 20227], "color": "#4caf50"},
    7: {"name": "Tropical/Sub-tropical Shrubland", "codes": [21450, 13476], "color": "#a1887f"},
    8: {"name": "Temp/Sub-polar Shrubland", "codes": [21450, 12050], "color": "#8d6e63"},
    9: {"name": "Tropical/Sub-tropical Grassland", "codes": [21669], "color": "#dce775"},
    10: {"name": "Temp/Sub-polar Grassland", "codes": [21537, 12212], "color": "#c0ca33"},
    11: {"name": "Sub-polar Shrub–Lichen–Moss", "codes": [20022, 21454, 21439], "color": "#b0bec5"},
    12: {"name": "Sub-polar Grass–Lichen–Moss", "codes": [21454, 20022, 21439], "color": "#90a4ae"},
    13: {"name": "Sub-polar Barren–Lichen–Moss", "codes": [21468, 21454, 20022], "color": "#78909c"},
    14: {"name": "Wetland", "codes": [42349, 41809], "color": "#26c6da"},
    15: {"name": "Cropland", "codes": [10037, 10025, 21441, 21453], "color": "#ffeb3b"},
    16: {"name": "Barren Lands", "codes": [6001, 6004], "color": "#bcaaa4"},
    17: {"name": "Urban and Built-up", "codes": [5003], "color": "#e53935"},
    18: {"name": "Water", "codes": [8001, 7001], "color": "#1e88e5"},
    19: {"name": "Snow and Ice", "codes": [8005, 8008], "color": "#e0f7fa"}
}


# --------------------------------------------------
# Build lookup tables
# --------------------------------------------------
code_to_class = {}
class_colors_list = []
class_names = []

for class_id in sorted(class_colors.keys()):
    info = class_colors[class_id]
    class_names.append(info["name"])
    class_colors_list.append(info["color"])
    for code in info["codes"]:
        code_to_class[code] = class_id - 1  # 0-based index


# --------------------------------------------------
# Reproject to EPSG:4326 using nearest neighbor
# --------------------------------------------------
print("Reprojecting to lat/lon...")
cec_ll = cec_clip.rio.reproject(
    "EPSG:4326",
    resolution=0.05,
    resampling=rasterio.enums.Resampling.nearest
)


# --------------------------------------------------
# Reclassify codes → class indices
# --------------------------------------------------
print("Reclassifying...")
def reclassify_codes(da, lookup):
    out = xr.full_like(da, np.nan, dtype=np.float32)
    for code, cls in lookup.items():
        out = out.where(da != code, cls)
    return out

cec_class = reclassify_codes(cec_ll, code_to_class)


# --------------------------------------------------
# Mode coarsening
# --------------------------------------------------
print("Coarsening (mode)...")
def mode_coarsen(da, x=18, y=18):
    def _mode(arr):
        arr = arr[~np.isnan(arr)].astype(int)
        if arr.size == 0:
            return np.nan
        return np.bincount(arr).argmax()

    return da.coarsen(x=x, y=y, boundary="trim").reduce(_mode)

cec_plot = mode_coarsen(cec_class, x=18, y=18)


# --------------------------------------------------
# Plot
# --------------------------------------------------
cmap = mcolors.ListedColormap(class_colors_list)
norm = mcolors.BoundaryNorm(
    np.arange(-0.5, len(class_colors_list) + 0.5),
    len(class_colors_list)
)

print("Plotting...")
fig, ax = plt.subplots(
    figsize=(16, 12),
    subplot_kw={"projection": ccrs.PlateCarree()}
)

im = cec_plot.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap=cmap,
    norm=norm,
    add_colorbar=True,
    cbar_kwargs={
        "ticks": np.arange(len(class_names)),
        "label": "Land Cover Class"
    }
)

im.colorbar.set_ticklabels(class_names)

ax.set_title("CEC Land Cover with Dust Origins")
ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=0.8)
ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)
ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)

soil_orders._plot_save(fig, plot_dir="figures", plot_name="cec_land_cover")
