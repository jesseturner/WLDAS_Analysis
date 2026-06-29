#--- Dust points dataframe with winds, moisture, static data (soil texture, soil order, and surface cover)

from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
import sys, os
import rioxarray as rxr
from datetime import datetime

def main():
    location_name = "American Southwest"
    dust_path = "DATA/raw/line_dust/Line_GOES-Dust_Date-LatLon-UTC_2001-2020_Sep2025.csv"
    dust_df = get_dust_df(dust_path)

    #--- wind data
    processed_wind_path = Path("DATA/processed/2_wind_grid_narr_2026-06-15.nc")
    # dust_df = add_winds_era5_to_dust_df(processed_wind_path, dust_df)
    dust_df = add_winds_narr_to_dust_df(processed_wind_path, dust_df)
    print(f"THIS SHOULD BE 3492: {len(dust_df)}")

    #--- moisture data
    processed_moisture_path = Path("DATA/processed/1_moisture_grid_2026-06-29.nc")
    dust_df = add_moisture_to_dust_df(processed_moisture_path, dust_df)

    #--- category data
    dust_df = add_static_data(dust_df, location_name)

    #--- save dataset
    timestamp = datetime.today().strftime("%Y-%m-%d")
    dust_df.to_csv(f"DATA/processed/3_dust_points_vars_{timestamp}.csv", index=False)

    return

#------------------------

def get_dust_df(dust_path):
    print("Opening dust data, creating dust dataframe... ")
    dust_df = pd.read_csv(dust_path)

    dust_df["time_str"] = (
        dust_df["start_time_utc"]
        .astype("Int64")        # allows NaNs safely
        .astype(str)
        .str.zfill(4)
    )

    dust_df["datetime"] = pd.to_datetime(
        dust_df["date"].astype(str) + dust_df["time_str"],
        format="%Y%m%d%H%M",
        utc=True,
        errors="coerce"
    )

    n_before = len(dust_df)
    dust_df = dust_df.dropna(subset=["datetime"]).copy()
    n_after = len(dust_df)
    n_removed = n_before - n_after
    print(f"Removed {n_removed} dust events due to invalid datetime parsing.")

    dust_df["datetime"] = (
        dust_df["datetime"]
        .dt.tz_convert(None)
    )
    return dust_df

def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

def add_winds_era5_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")
    dust_winds = []
    for _, row in dust_df.iterrows():
        
        #--- Day-of time match 
        ws = ds_ws["wind_speed"].sel(
            time=row["datetime"].normalize() + np.timedelta64(12, "h") #--- Making sure this matches to datetime in wind speed
        ).sel(
            latitude=row["latitude"],
            longitude=row["longitude"],
            method="nearest"
        )
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds

    return dust_df

def add_winds_narr_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")
    lat2d = ds_ws["lat"].values
    lon2d = ds_ws["lon"].values

    dust_winds = []
    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        
        #--- Day-of time match 
        ws = ds_ws["wind_speed"].sel(
            time=row["datetime"].normalize() + np.timedelta64(12, "h") #--- Making sure this matches to datetime in wind speed
            ).isel(y=iy, x=ix)
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds

    return dust_df

def open_gldas_file(gldas_path):
    ds = xr.open_dataset(gldas_path)
 