#--- This is a plot of the average moisture before and after each dust event
#--- I made a version of this many months ago, but this is the new one

from pathlib import Path
import xarray as xr
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
from datetime import timedelta
from tqdm import tqdm

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

    moist_time_range = get_moisture_trends(wldas_total, dust_df)

    plot_time_range(moist_time_range)

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

def get_moisture_trends(wldas_total, dust_df):

    dust_times = dust_df['datetime'].dt.floor("D").values

    moist_anytime = []
    moist_anytime = wldas_total['SoilMoi00_10cm_tavg']

    print("\n Moisture anytime shape:", np.shape(moist_anytime))

    #--- Preallocate the array
    n_events = len(dust_times)+1
    time_window = 60
    moist_time_range = np.empty((n_events, time_window))

    time_index = moist_anytime.get_index("time")
    count_skipped = 0

    for index, event in tqdm(dust_df.iterrows(), total=len(dust_df), desc="Processing rows"):
        dust_lat = event['latitude']
        dust_lon = event['longitude']
        dust_time = event['datetime'].floor("D")
        idx = time_index.get_indexer([dust_time], method="nearest")[0]
        start = max(0, idx - 30)
        end = start + time_window
        moist_time_slice = moist_anytime.isel(time=slice(start, end))
        try:
            moist_time_range[index] = moist_time_slice.sel(lat=dust_lat, lon=dust_lon, method="nearest")
        except:
            count_skipped += 1

    print(f"Skipped {count_skipped} (probably out of range)...")
    print("\n Shape of moisture time range array:", np.shape(moist_time_range))

    return moist_time_range

def plot_time_range(moist_time_range):

     #--- Adjust so beginning is 30 days before
    time = np.arange(moist_time_range.shape[1])-30

    plt.figure(figsize=(12, 6))

    #--- Remove the points that did not run fully
    moist_time_range[moist_time_range == 0] = np.nan

    #--- Plotting the mean and std of the series
    mean_series = np.nanmean(moist_time_range, axis=0)
    std_series = (np.nanstd(moist_time_range, axis=0)) ** 1/5
    plt.plot(time, mean_series, color='black', linewidth=3, 
             marker='o', markersize=9, 
             label='Mean', zorder=9)
    plt.fill_between(
        time,
        mean_series - std_series,
        mean_series + std_series,
        alpha=0.3, 
        label="±1 std"
    )
    plt.axvline(x=0, linestyle='-', alpha=0.3, linewidth=6)

    plt.tick_params(axis='both', labelsize=15)
    plt.xticks(np.arange(-30, 31, 6))
    plt.xlabel('Days From Dust Event', fontsize=15)
    plt.ylabel('Soil Moisture (0-10 cm) [m³/m³]', fontsize=15)
    plt.title('Average soil moisture associated with each blowing dust event', fontsize=18, pad=12)
    plt.tight_layout()
    plt.savefig(os.path.join("figures", "2_soil_moisture_1_average_trend"), bbox_inches='tight', dpi=300)

    return

#------------------------

if __name__ == "__main__":
    main()