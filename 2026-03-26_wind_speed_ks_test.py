#--- Here I am just calculating the K-S statistic for the wind distribution plot
#--- If you want the plot, use 2026-03-24

from pathlib import Path
import xarray as xr
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from modules_line_dust import line_dust_utils as dust

def main():
    ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
    wind_speed_ds = get_wind_speed_ds(ws_data_path)    

    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    ws_currently_blowing, ws_anytime = get_wind_speed_at_dust_origins(wind_speed_ds, dust_df)

    print("\n WS currently blowing \n", np.shape(ws_currently_blowing))

    print("\n WS anytime \n", np.shape(ws_anytime))

    run_ks_test(ws_currently_blowing, ws_anytime)

    return

#------------------------

def get_wind_speed_ds(ws_data_path):
    if ws_data_path.exists():
        print("Loading wind speed data...")
        #--- Chunking makes a huge difference with speed
        ds_ws = xr.open_dataset(ws_data_path, chunks={"time": 100})
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()

    return ds_ws

def get_dust_df(dust_path):
    print("Opening dust data, creating dust dataframe... ")
    dust_df = dust.read_dust_data_into_df(dust_path)

    dust_df["time_str"] = (
        dust_df["start time (UTC)"]
        .astype("Int64")        # allows NaNs safely
        .astype(str)
        .str.zfill(4)
    )

    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"].astype(str) + dust_df["time_str"],
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

def get_wind_speed_at_dust_origins(wind_speed_ds, dust_df):

    y_indices, x_indices, time_indices = match_dust_and_wind_speed_grids(wind_speed_ds, dust_df)

    ws_currently_blowing = []
    ws_anytime = []

    print("Extracting wind speeds at dust events and for whole time range...")

    #--- Day-of time match 
    ws_currently_blowing = wind_speed_ds["wind_speed"].isel(
        y=xr.DataArray(y_indices, dims="points"),
        x=xr.DataArray(x_indices, dims="points"),
        time=xr.DataArray(time_indices, dims="points")
    )

    #--- Full time domain match 
    ws_anytime = wind_speed_ds["wind_speed"].isel(
        y=xr.DataArray(y_indices, dims="points"),
        x=xr.DataArray(x_indices, dims="points"),
    )
    
    return ws_currently_blowing, ws_anytime

def nearest_grid_point(ws_lat2d, ws_lon2d, dust_lat, dust_lon):
    dist2 = (ws_lat2d - dust_lat)**2 + (ws_lon2d - dust_lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

def match_dust_and_wind_speed_grids(wind_speed_ds, dust_df):
    print("Spatial matching of wind grid (Lambert Conformal)...")

    lat2d = wind_speed_ds["lat"].values
    lon2d = wind_speed_ds["lon"].values

    y_indices = []
    x_indices = []
    time_indices = []
    
    time_index = wind_speed_ds["time"].to_index()

    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        y_indices.append(iy.item())
        x_indices.append(ix.item())

        #--- Get datatime index
        t = row["datetime"].floor("D")
        it = time_index.get_indexer([t], method="nearest")[0]
        time_indices.append(it)

    return y_indices, x_indices, time_indices

def run_ks_test(ws_currently_blowing, ws_anytime):
    from scipy.stats import ks_2samp

    samples1 = ws_currently_blowing.values.ravel()
    samples2 = ws_anytime.values.ravel()

    samples1 = samples1[np.isfinite(samples1)]
    samples2 = samples2[np.isfinite(samples2)]

    stat, pval = ks_2samp(samples1, samples2)

    print(f"Stat: {stat}")
    print(f"Pval: {pval}")

    return

#------------------------

if __name__ == "__main__":
    main()