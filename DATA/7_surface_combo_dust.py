'''
Dataset made from the finest resolution surface map, 
with a count of dust events binned on those pixels.
Similar to control_grid, but without time-changing fields, is at full resolution, 
and includes dust points.
'''

import xarray as xr
import numpy as np
import rioxarray as rxr
from pyproj import CRS, Transformer
import rasterio
import pandas as pd
from datetime import datetime
import os
import xesmf as xe  

def main():

    dust_df = pd.read_csv("DATA/processed/3_dust_points_vars_2026-07-13.csv")
    wind_grid = xr.open_dataset("DATA/processed/2_wind_grid_narr_2026-06-15.nc")

    texture_da = get_texture_map()
    soil_da = get_soil_order_map()
    cec_ds = get_land_cover_map()

    combo_three_ds = create_combo_id_on_common_grid(texture_da, soil_da, cec_ds)
    combo_three_ds = bin_dust_events_on_common_grid(combo_three_ds, dust_df)
    combo_three_ds = merge_wind_narr_on_common_grid(combo_three_ds, wind_grid)

    #--- save dataset
    timestamp = datetime.today().strftime("%Y-%m-%d")
    processed_data_path = f"DATA/processed/7_surface_combo_dust_{timestamp}.nc"
    combo_three_ds.to_netcdf(processed_data_path)
    print(f"Saved dataset to {processed_data_path}")

    return

#------------------------

def _get_coords_for_region(location_name):
    '''
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    '''
    locations = {
        "American Southwest": [(43, -124), (25, -97)],

        "Chihuahua": [(33.3, -110.0), (28.0, -105.3)],
        "West Texas": [(35.0, -104.0), (31.8, -100.5)],
        "Central High Plains": [(43.0, -105.0), (36.5, -98.0)],
        "Nevada": [(43.0, -120.7), (37.0, -114.5)],
        "Utah": [(42.0, -114.5), (37.5, -109.0)],
        "Southern California": [(37.0, -119.0), (30.0, -114.2)],
        "Four Corners": [(37.5, -112.5), (34.4, -107.0)],
        "San Luis Valley": [(38.5, -106.5), (37.0, -105.3)],

        "N Mexico 1": [(31.8, -107.6), (31.3, -107.1)],
        "Carson Sink": [(40.1, -118.75), (39.6, -118.25)],
        "N Mexico 2": [(31.4, -108.25), (30.9, -107.75)],
        "N Mexico 3": [(31.1, -107.15), (30.6, -106.65)],
        "Black Rock 1": [(41.15, -119.35), (40.65, -118.85)],
        "West Texas 1": [(32.95, -102.35), (32.45, -101.85)],
        "N Mexico 4": [(30.65, -107.65), (30.15, -107.15)],
        "N Mexico 5": [(31.0, -106.65), (30.5, -106.15)],
        "White Sands": [(33.15, -106.6), (32.65, -106.1)],
        "West Texas 2": [(33.5, -102.8), (33.0, -102.30)],
        "SLV2": [(38.05, -106.15), (37.55, -105.65)],
        "N Mexico 6": [(29.55, -107.05), (29.05, -106.55)],
        "NE AZ": [(35.7, -111.1), (35.2, -110.6)],
        "NW New Mexico": [(36.15, -108.85), (35.65, -108.35)],
        "Black Rock 2": [(40.75, -119.9), (40.25, -119.4)],
        "N Mexico 7": [(30.9, -108.15), (30.4, -107.65)],
    }
    coords = locations[location_name]
    lats = [p[0] for p in coords]
    lons = [p[1] for p in coords]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    return lat_min, lat_max, lon_min, lon_max

def get_texture_map():
    location_name = "American Southwest"
    gldas_path = "DATA/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
    texture_ds = xr.open_dataset(gldas_path)
    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    filtered_ds = texture_ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max)
    )

    texture_da = filtered_ds.GLDAS_soiltex

    return texture_da


def get_soil_order_map():
    orders_filepath = "DATA/raw/soil_orders_usda/soil_major_orders_2026-06-22.nc"
    soil_da = xr.open_dataarray(orders_filepath)
    return soil_da

def get_cec_land_cover_reprojection(cec_full, location_name):
    min_lat, max_lat, min_lon, max_lon = _get_coords_for_region(location_name)
    min_lat_extend = min_lat - 5
    max_lat_extend = max_lat + 4

    src_crs = CRS.from_epsg(4326) 
    dst_crs = CRS.from_wkt(cec_full.rio.crs.to_wkt()) 
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True) 
    minx, miny = transformer.transform(min_lon, min_lat_extend) 
    maxx, maxy = transformer.transform(max_lon, max_lat_extend) 
    minx, maxx = sorted([minx, maxx]) 
    miny, maxy = sorted([miny, maxy]) 
    cec_cropped = cec_full.rio.clip_box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    output_path = "DATA/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
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

    return cec

def get_land_cover_map():
    location_name = "American Southwest"
    cec_filepath = ("DATA/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif")
    cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)
    cec_ds = get_cec_land_cover_reprojection(cec_full, location_name)

    return cec_ds

def create_combo_id_on_common_grid(texture_da, soil_da, cec_ds):

    cec_ds_ll = cec_ds.rename({"x": "lon", "y": "lat"})

    def get_resolution(da):
        return abs(da.lat.diff("lat").mean().item()), abs(da.lon.diff("lon").mean().item())

    resolutions = [get_resolution(cec_ds_ll), get_resolution(soil_da), get_resolution(texture_da)]

    dlat, dlon = min(resolutions, key=lambda x: x[0] * x[1])

    lat_new = np.arange(
        min(cec_ds_ll.lat.min(), soil_da.lat.min(), texture_da.lat.min()),
        max(cec_ds_ll.lat.max(), soil_da.lat.max(), texture_da.lat.max()) + dlat,
        dlat
    )

    lon_new = np.arange(
        min(cec_ds_ll.lon.min(), soil_da.lon.min(), texture_da.lon.min()),
        max(cec_ds_ll.lon.max(), soil_da.lon.max(), texture_da.lon.max()) + dlon,
        dlon
    )

    #--- Interpolate onto new grid

    cec_hi = cec_ds_ll.interp(lat=lat_new, lon=lon_new, method="nearest")
    soil_hi = soil_da.interp(lat=lat_new, lon=lon_new, method="nearest")
    texture_hi = texture_da.interp(lat=lat_new, lon=lon_new, method="nearest")

    combo_three_ds = xr.Dataset({
        "surface_cover": cec_hi,
        "soil_order": soil_hi,
        "texture": texture_hi,
    })

    #--- Cleaning up the dataset

    combo_three_ds = combo_three_ds.squeeze("time")
    combo_three_ds['surface_cover'] = combo_three_ds['surface_cover'].round().astype(float)
    combo_three_ds['soil_order'] = combo_three_ds['soil_order'].round().astype(float)
    combo_three_ds['texture'] = combo_three_ds['texture'].round().astype(float)

    #--- Creating combo ID

    combo_three_ds["combo_id"] = (
        combo_three_ds["texture"] * 1_000_000 +
        combo_three_ds["soil_order"] * 1_000 +
        combo_three_ds["surface_cover"]
    )

    return combo_three_ds

def bin_dust_events_on_common_grid(combo_three_ds, dust_df):

    lat = combo_three_ds.lat.values
    lon = combo_three_ds.lon.values

    lat_edges = np.concatenate([
        [lat[0] - (lat[1] - lat[0]) / 2],
        (lat[:-1] + lat[1:]) / 2,
        [lat[-1] + (lat[-1] - lat[-2]) / 2]
    ])

    lon_edges = np.concatenate([
        [lon[0] - (lon[1] - lon[0]) / 2],
        (lon[:-1] + lon[1:]) / 2,
        [lon[-1] + (lon[-1] - lon[-2]) / 2]
    ])

    counts, _, _ = np.histogram2d(
        dust_df["latitude"],
        dust_df["longitude"],
        bins=[lat_edges, lon_edges]
    )

    combo_three_ds["dust_event_count"] = (("lat", "lon"), counts)
    
    return combo_three_ds

def merge_wind_narr_on_common_grid(combo_three_ds, wind_grid):
    print("Merging winds onto common grid...")
    target_grid = xr.Dataset(
        {
            "lat": (["lat"], combo_three_ds.lat.values),
            "lon": (["lon"], combo_three_ds.lon.values),
        }
    )
    source_grid = xr.Dataset(
        {
            "lat": (["y", "x"], wind_grid.lat.values),
            "lon": (["y", "x"], wind_grid.lon.values),
        }
    )
    regridder = xe.Regridder(
        source_grid,
        target_grid,
        method="bilinear",
        periodic=False
    )

    wind_regridded = regridder(wind_grid["wind_speed"])
    wind_regridded["time"] = wind_regridded.indexes["time"].normalize()

    merged_grid = xr.merge([
        combo_three_ds,
        wind_regridded.to_dataset(name="wind_speed")
    ])

    return merged_grid

#------------------------

if __name__ == "__main__":
    main()
