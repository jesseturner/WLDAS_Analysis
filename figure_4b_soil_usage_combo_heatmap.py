import rioxarray as rxr
from pyproj import CRS, Transformer
import rasterio
import os
import xarray as xr

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders
from modules_texture import gldas_texture_utils as gldas

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
top15 = combo_counts.head(15).copy()

#--- Count combinations total
usage_df = usage.to_dataframe(name="usage").reset_index()
print(usage_df)

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
top15_total = combo_counts_total.head(15).copy()

#--- Map to category names
soil_order_dict = orders.get_soil_order_dict() 
soil_order_colors = orders.get_category_colors()
#---CONTINUE HERE