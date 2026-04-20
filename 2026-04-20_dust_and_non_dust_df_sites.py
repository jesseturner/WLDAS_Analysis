#--- This figure compares moisture values associated for dust and for non-dust, 
#--- using only where wind speeds are >= 10 m/s

from pathlib import Path
import xarray as xr
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt
import sys

from modules_line_dust import line_dust_utils as dust

def main():
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    #--- moisture data
    processed_wldas_path = Path("data/processed/wldas_sample/wldas_total_2026_02_18.nc")
    wldas_path = "/mnt/data2/jturner/wldas_data"
    wldas_dust_days = option_to_rerun_cached_moisture(wldas_path, processed_wldas_path, dust_df, is_rerun=False)

    #--- create non-dust dataframe
    non_dust_df = create_non_dust_df(dust_df)
    non_dust_df_sample = non_dust_df.sample(n=100_000, random_state=9)

    #--- moisture data
    processed_wldas_path = Path("data/processed/wldas_sample/wldas_sample_all_2026_04_20.nc")
    wldas_path = "/mnt/data2/jturner/wldas_data"
    wldas_sample_all = option_to_rerun_cached_moisture(wldas_path, processed_wldas_path, non_dust_df_sample, is_rerun=True)

    #--- wind data
    processed_wind_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")

    #--- get histograms
    dust_df = add_winds_to_dust_df(processed_wind_path, dust_df)
    dust_df = add_wldas_moisture_to_dust_df(wldas_dust_days, dust_df)
    non_dust_df = add_winds_to_dust_df(processed_wind_path, non_dust_df_sample)
    non_dust_df = add_wldas_moisture_to_dust_df(wldas_sample_all, non_dust_df_sample)

    print(dust_df)
    print(non_dust_df)

    dust_df.to_csv("data/processed/dust_and_non_dust/dust.csv", index=False)
    non_dust_df.to_csv("data/processed/dust_and_non_dust/non_dust_at_sites.csv", index=False)

    sys.exit()

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

def create_wldas_dust_days(wldas_path, dust_df):
    print("Opening WLDAS files for each dust date...")
    
    wldas_files_every_dust = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['datetime'].dt.strftime('%Y%m%d')
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
    wldas_dust_days = xr.open_mfdataset(
        existing_files,
        combine="by_coords",
        drop_variables="time_bnds"
    )
    return wldas_dust_days

def saving_processed_files(processed_wldas_path, wldas_set):
    print("Saving processed files as NetCDFs...")
    processed_wldas_path.parent.mkdir(parents=True, exist_ok=True)

    #--- Coarsen resolution for wldas_set
    COARSEN_LAT = 24
    COARSEN_LON = 24
    wldas_set = (
        wldas_set
        .coarsen(lat=COARSEN_LAT, lon=COARSEN_LON, boundary="trim")
        .mean()
    )

    wldas_set.to_netcdf(processed_wldas_path)
    print(f"Saved wldas set to {processed_wldas_path}")

    return

def option_to_rerun_cached_moisture(wldas_path, processed_wldas_path, dust_df, is_rerun):
    '''
    :param processed_wldas_path: Path("data/processed/wldas_sample")
    :param is_rerun: Boolean
    '''
    if is_rerun:
        print("--- Rerunning WLDAS processing into xarray datasets ---")
        wldas_total = create_wldas_dust_days(wldas_path, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        #--- Seems to have some good default chunking scheme, 
        #--- gives me a warning when I try to implement my own

    wldas_dust_days = xr.open_dataset(processed_wldas_path)

    return wldas_dust_days

def create_non_dust_df(dust_df):
    print("Creating the non-dust dataframe...")

    lat_lon = dust_df[["latitude", "longitude"]].drop_duplicates()
    dates = pd.date_range(start="2001-01-01", end="2020-12-31", freq="D")
    dust_dates = pd.to_datetime(dust_df["datetime"]).dt.normalize().unique()
    filtered_dates = dates[~dates.isin(dust_dates)]
    dates_df = pd.DataFrame({"date": filtered_dates})
    non_dust_df = lat_lon.merge(dates_df, how="cross")
    non_dust_df["datetime"] = pd.to_datetime(non_dust_df["date"])
    non_dust_df = non_dust_df.drop(columns="date")

    print(f"Non-dust dataframe: {np.shape(non_dust_df)}, from {len(filtered_dates)} non-dust days...")

    return non_dust_df


def add_winds_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")

    def nearest_grid_point(lat2d, lon2d, lat, lon):
        dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
        iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
        return iy, ix
    lat2d = ds_ws["lat"].values
    lon2d = ds_ws["lon"].values

    dust_winds = []
    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        
        #--- Day-of time match 
        ws = ds_ws["wind_speed"].sel(
            time=row["datetime"].floor("D"),
            method="nearest"
        ).isel(y=iy, x=ix)
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds
    dust_df = dust_df.dropna(subset=["wind_speed"])

    return dust_df

def add_wldas_moisture_to_dust_df(wldas_set, dust_df):
    print("Adding WLDAS moisture to dust dataframe...")

    wldas_dates = pd.to_datetime(wldas_set.time.values).normalize()
    wldas_dates_set = set(wldas_dates.values)

    dust_df['moisture'] = None
    skipped_no_wldas_date = 0

    for idx, row in dust_df.iterrows():
        dust_time = row['datetime'].normalize()

        if dust_time.to_datetime64() not in wldas_dates_set:
            skipped_no_wldas_date += 1
            continue

        try:
            wldas_point = wldas_set.sel(
                time=dust_time,
                lat=row['latitude'],
                lon=row['longitude'],
                method="nearest"
            )['SoilMoi00_10cm_tavg'].values.item()

            dust_df.at[idx, 'moisture'] = wldas_point

        except KeyError as e:
            print(f"Skipping row {idx}: {e}")

    print(f"Total dust points: {len(dust_df)}")
    print(f"Skipped (no matching WLDAS date): {skipped_no_wldas_date}")
    print(f"Dust points tracked: {dust_df['moisture'].notna().sum()}")

    return dust_df

#------------------------

if __name__ == "__main__":
    main()