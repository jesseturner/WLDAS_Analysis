import xarray as xr
import pandas as pd
import numpy as np

from modules_soil_orders import soil_orders_utils as soil_orders

print("WARNING: 20 years of data takes about 30 minutes to run.")

print("Opening data from NARR...")

ds_uwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/uwnd.10m.20*.nc")
ds_vwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/vwnd.10m.20*.nc")

def get_daytime_max_ws(ds):
    ds_sel = ds.sel(time=ds.time.dt.hour.isin([0, 12, 15, 18, 21]))

    #--- Shift 00 UTC back one day (to match with correct daily group)
    time_shifted = ds_sel.time.where(
        ds_sel.time.dt.hour != 0,
        ds_sel.time - pd.Timedelta(days=1)
    )

    ds_sel = ds_sel.assign_coords(time=time_shifted)

    #--- Resample to get daily maximum
    ds_sel = ds_sel.sortby("time") 
    ds_daily = ds_sel.resample(time="1D").max()
    ds_daily["time"] = ds_daily.time + pd.Timedelta(hours=12)
    
    return ds_daily

print("Limiting to maximum from 12, 15, 18, 21, 00 UTC...")
daily_uwnd = get_daytime_max_ws(ds_uwnd)
daily_vwnd = get_daytime_max_ws(ds_vwnd)

print("Calculating wind speed...")
wind_speed = np.sqrt(daily_uwnd.uwnd**2 + daily_vwnd.vwnd**2)
ds_daytime_ws = wind_speed.to_dataset(name="wind_speed")

print("Cropping to American Southwest...")
min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region("American Southwest")
lat = ds_daytime_ws["lat"]
lon = ds_daytime_ws["lon"]
mask = (
    (lat >= min_lat) & (lat <= max_lat) &
    (lon >= min_lon) & (lon <= max_lon)
).compute()
ds_daytime_ws = ds_daytime_ws.where(mask, drop=True)

print("Cropping to land mask...")
land_mask = xr.open_dataset("/mnt/data2/jturner/narr/land.nc")
land_mask = land_mask.squeeze("time", drop=True)
land_mask_bool = land_mask['land'].astype(bool)
ds_daytime_ws = ds_daytime_ws.where(land_mask_bool)

print("Saving to netcdf...")
processed_path = "/mnt/data2/jturner/narr/processed"
ds_daytime_ws.to_netcdf(f"{processed_path}/narr_daytime_wnd_max.nc")