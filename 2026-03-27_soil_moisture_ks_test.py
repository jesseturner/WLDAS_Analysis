#--- Here I am just calculating the K-S statistic for the moisture distribution plot
#--- If you want the plot, use 2026-03-25

from pathlib import Path
import xarray as xr
import rioxarray as rxr
import pandas as pd
import os
from pyproj import CRS, Transformer
import rasterio
import numpy as np

from modules_line_dust import line_dust_utils as dust

def main():
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    #--- Paths for cached and raw datasets
    processed_wldas_path = Path("data/processed/wldas_sample")
    wldas_path = "/mnt/data2/jturner/wldas_data"

    #--- Option to re-run the cached moisture datasets
    rerun_moisture_data = False
    if rerun_moisture_data:
        print("--- Rerunning WLDAS processing into xarray datasets ---")
        wldas_total = create_wldas_total(wldas_path, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        #--- Seems to have some good default chunking scheme, 
        #--- gives me a warning when I try to implement my own
        wldas_total = xr.open_dataset(processed_wldas_path / "wldas_total_2026_02_18.nc")

    moist_currently_blowing, moist_anytime = get_moisture_at_dust_origins(wldas_total, dust_df)

    print("\n WS currently blowing \n", np.shape(moist_currently_blowing))

    print("\n WS anytime \n", np.shape(moist_anytime))

    run_ks_test(moist_currently_blowing, moist_anytime)

    return

#------------------------

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

def create_wldas_total(wldas_path, dust_df):
    print("Opening WLDAS files for each dust date...")
    
    wldas_files_every_dust = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['Date (YYYYMMDD)'].astype(str)
    ]

    existing_files = []
    missing_files = []

    for f in wldas_files_every_dust:
        if Path(f).exists():
            existing_files.append(f)
        else:
            missing_files.append(f)
    if missing_files:
        print(f"WARNING: {len(missing_files)} files from dust dataframe not found in WLDAS:")
        for f in missing_files:
            print(f"  - {f}")

    print(f"Opening {len(existing_files)}/{len(wldas_files_every_dust)} WLDAS files...")    
    wldas_total = xr.open_mfdataset(
        existing_files,
        combine="by_coords",
        drop_variables="time_bnds"
    )
    return wldas_total

def saving_processed_files(processed_wldas_path, wldas_total):
    print("Saving processed files as NetCDFs...")
    processed_wldas_path.parent.mkdir(parents=True, exist_ok=True)

    #--- Coarsen resolution for wldas_total
    COARSEN_LAT = 24
    COARSEN_LON = 24
    wldas_total = (
        wldas_total
        .coarsen(lat=COARSEN_LAT, lon=COARSEN_LON, boundary="trim")
        .mean()
    )

    wldas_total.to_netcdf(processed_wldas_path / "wldas_total_18.nc")
    print(f"Saved wldas_total → {processed_wldas_path}")

    return

def get_moisture_at_dust_origins(wldas_total, dust_df):

    dust_lats = dust_df['latitude'].values
    dust_lons = dust_df['longitude'].values
    dust_times = dust_df['datetime'].dt.floor("D").values

    moist_currently_blowing = []
    moist_anytime = []

    print("Extracting moistures at dust events and for whole time range...")

    points = xr.DataArray(range(len(dust_lats)), dims="points")

    #--- Day-of time match 
    moist_currently_blowing = wldas_total.sel(
        lat=xr.DataArray(dust_lats, dims="points"),
        lon=xr.DataArray(dust_lons, dims="points"),
        time=xr.DataArray(dust_times, dims="points"),
        method="nearest"
    )
    moist_currently_blowing = moist_currently_blowing['SoilMoi00_10cm_tavg']

    #--- Full time domain match 
    moist_anytime = wldas_total.sel(
        lat=xr.DataArray(dust_lats, dims="points"),
        lon=xr.DataArray(dust_lons, dims="points"),
        method="nearest"
    )
    moist_anytime = moist_anytime['SoilMoi00_10cm_tavg']

    return moist_currently_blowing, moist_anytime

def run_ks_test(moist_currently_blowing, moist_anytime):
    from scipy.stats import ks_2samp

    samples1 = moist_currently_blowing.values.ravel()
    samples2 = moist_anytime.values.ravel()

    samples1 = samples1[np.isfinite(samples1)]
    samples2 = samples2[np.isfinite(samples2)]

    stat, pval = ks_2samp(samples1, samples2)

    print(f"Stat: {stat}")
    print(f"Pval: {pval}")

    return


#------------------------

if __name__ == "__main__":
    main()