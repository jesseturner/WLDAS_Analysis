import xarray as xr
import pandas as pd
import numpy as np

from modules_soil_orders import soil_orders_utils as soil_orders

print("WARNING: 20 years of data takes about 30 minutes to run.")

print("Opening data from NARR...")

ds_uwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/uwnd.10m.20*.nc")
ds_vwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/vwnd.10m.20*.nc")

print("Calculating wind speed...")
wind_speed = np.sqrt(ds_uwnd.uwnd**2 + ds_vwnd.vwnd**2)
ds_ws = wind_speed.to_dataset(name="wind_speed")

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

print("Cropping to American Southwest...")
min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region("American Southwest")
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

print("Saving to netcdf...")
processed_path = "/mnt/data2/jturner/narr/processed"
ds_daytime_max.to_netcdf(f"{processed_path}/narr_daytime_wnd_max.nc")