#--- NetCDF file with NARR wind speeds from 2001-2020 for the American Southwest
#--- Saved at /mnt/data2/jturner/narr/processed

import xarray as xr
import pandas as pd
import numpy as np

def main(): 
    print("WARNING: 20 years of data takes about 30 minutes to run.")

    ds_ws = get_wind_speeds()

    ds_daytime_max = get_daytime_max_ws(ds_ws)
    
    ds_daytime_max = crop_to_region_and_land(ds_daytime_max)

    print("Saving to netcdf...")
    processed_path = "/mnt/data2/jturner/narr/processed"
    ds_daytime_max.to_netcdf(f"{processed_path}/narr_daytime_wnd_max.nc")

    return

#------------------------

def get_wind_speeds():   
    print("Opening data from NARR...")
    ds_uwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/uwnd.10m.20*.nc")
    ds_vwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/vwnd.10m.20*.nc")

    print("Calculating wind speed...")
    wind_speed = np.sqrt(ds_uwnd.uwnd**2 + ds_vwnd.vwnd**2)
    ds_ws = wind_speed.to_dataset(name="wind_speed")

    return ds_ws

def get_daytime_max_ws(ds_ws):

    print("Getting max winds from daytime (12, 15, 18, 21, 00 UTC)...")
    ds_daytime = ds_ws.sel(time=ds_ws.time.dt.hour.isin([0, 12, 15, 18, 21]))

    #--- Shift 00 UTC back one day (to match with correct daily group)
    time_shifted = ds_daytime.time.where(
        ds_daytime.time.dt.hour != 0,
        ds_daytime.time - pd.Timedelta(days=1)
    )

    ds_daytime = ds_daytime.assign_coords(time=time_shifted)

    ds_daytime = ds_daytime.sortby("time")
    ds_daytime_max = ds_daytime.resample(time="1D").max()
    ds_daytime_max["time"] = ds_daytime_max.time + pd.Timedelta(hours=12)

    return ds_daytime_max

def crop_to_region_and_land(ds_daytime_max):
    
    print("Cropping to American Southwest...")
    min_lat, max_lat, min_lon, max_lon = _get_coords_for_region("American Southwest")
    lat = ds_daytime_max["lat"]
    lon = ds_daytime_max["lon"]
    mask = (
        (lat >= min_lat) & (lat <= max_lat) &
        (lon >= min_lon) & (lon <= max_lon)
    ).compute()
    ds_daytime_max = ds_daytime_max.where(mask, drop=True)

    print("Cropping to land mask...")
    land_mask = xr.open_dataset("/mnt/data2/jturner/narr/land.nc")
    land_mask = land_mask.squeeze("time", drop=True)
    land_mask_bool = land_mask['land'].astype(bool)
    ds_daytime_max = ds_daytime_max.where(land_mask_bool)

    return ds_daytime_max

def _get_coords_for_region(location_name):
    """
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    """
    locations = {
        "American Southwest": [(44, -128), (27.5, -100)],
        
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

#------------------------

if __name__ == "__main__":
    main()