#--- Dataset of dust points and all variables for 2001-2020
#--- Almost the same as control_grid, but only at dust regions

from datetime import datetime
import xarray as xr
import os
import rioxarray as rxr
import xesmf as xe  
import pandas as pd
import numpy as np

def main():

    moisture_grid = xr.open_dataset("DATA/processed/1_moisture_grid_2026-05-15.nc")
    wind_grid = xr.open_dataset("DATA/processed/2_wind_grid_narr_2026-04-23.nc")

    moisture_grid = merge_wind_onto_moisture(moisture_grid, wind_grid)
    moisture_grid = merge_usage_onto_moisture(moisture_grid)
    moisture_grid = merge_texture_onto_moisture(moisture_grid)
    moisture_grid = merge_orders_onto_moisture(moisture_grid)

    dust_path = "DATA/raw/line_dust/Line_GOES-Dust_Date-LatLon-UTC_2001-2020_Sep2025.csv"
    dust_df = pd.read_csv(dust_path)
    grid_dust_sites = mask_to_dust_sites(moisture_grid, dust_df)

    #--- save dataset
    timestamp = datetime.today().strftime("%Y-%m-%d")
    processed_wldas_path = f"DATA/processed/5_control_grid_dust_sites_{timestamp}.nc"
    grid_dust_sites.to_netcdf(processed_wldas_path)
    print(f"Saved wldas set to {processed_wldas_path}")

    return

#------------------------

def merge_wind_onto_moisture(moisture_grid, wind_grid):
    print("Merging winds onto moisture grid...")
    target_grid = xr.Dataset(
        {
            "lat": (["lat"], moisture_grid.lat.values),
            "lon": (["lon"], moisture_grid.lon.values),
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
        moisture_grid,
        wind_regridded.to_dataset(name="wind_speed")
    ])

    return merged_grid

def merge_usage_onto_moisture(moisture_grid):
    print("Merging usage onto moisture grid...")
    cover_data_path = "DATA/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
    if os.path.exists(cover_data_path):
        print("Opening surface usage dataset...")
        usage = rxr.open_rasterio(cover_data_path).squeeze("band", drop=True)
    else:
        print("Land cover data not found, exiting...")

    usage = usage.rename({
        "y": "lat",
        "x": "lon"
    })

    usage_interp = usage.interp(
        lat=moisture_grid.lat,
        lon=moisture_grid.lon,
        method="nearest"
    )

    moisture_grid["usage"] = usage_interp

    return moisture_grid

def merge_texture_onto_moisture(moisture_grid):
    print("Merging texture onto moisture grid...")
    gldas_path = "DATA/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
    texture_ds = open_gldas_file(gldas_path)
    texture_ds = filter_to_region(texture_ds, location_name="American Southwest")

    texture_da = texture_ds.GLDAS_soiltex
    texture_da = texture_da.squeeze("time", drop=True)

    texture_da_interp = texture_da.interp(
        lat=moisture_grid.lat,
        lon=moisture_grid.lon,
        method="nearest"
    )

    moisture_grid["soil_texture"] = texture_da_interp

    return moisture_grid

def merge_orders_onto_moisture(moisture_grid):
    print("Merging soil order onto moisture grid...")
    usda_filepath = "DATA/raw/soil_types_usda/global-soil-suborders-2022.tif"
    location_name="American Southwest"
    min_lat, max_lat, min_lon, max_lon = _get_coords_for_region(location_name)
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

    soil_da = soil_da.rename({
        "y": "lat",
        "x": "lon"
    })
    soil_da = soil_da.sortby("lat")
    soil_da_interp = soil_da.interp(
        lat=moisture_grid.lat,
        lon=moisture_grid.lon,
        method="nearest"
    )

    soil_da_interp = soil_da_interp.where(soil_da_interp != 255)
    moisture_grid["soil_order"] = soil_da_interp

    return moisture_grid

def open_gldas_file(gldas_path):
    ds = xr.open_dataset(gldas_path)
    return ds

def _get_coords_for_region(location_name):
    """
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    """
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

def filter_to_region(ds, location_name):

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    filtered_ds = ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max)
    )
    return filtered_ds

def mask_to_dust_sites(moisture_grid, dust_df):
    print("Masking for dust origin sites...")
    lat_vals = moisture_grid.lat.values
    lon_vals = moisture_grid.lon.values

    lat_idx = np.abs(
        lat_vals[:, None] - dust_df["latitude"].values
    ).argmin(axis=0)

    lon_idx = np.abs(
        lon_vals[:, None] - dust_df["longitude"].values
    ).argmin(axis=0)

    pairs = set(zip(lat_idx, lon_idx))

    mask = xr.DataArray(
        np.zeros((len(moisture_grid.lat), len(moisture_grid.lon)), dtype=bool),
        coords={"lat": moisture_grid.lat, "lon": moisture_grid.lon},
        dims=("lat", "lon"),
    )

    for i, j in pairs:
        mask[i, j] = True

    grid_dust_sites = moisture_grid.where(mask)

    return grid_dust_sites

#------------------------

if __name__ == "__main__":
    main()