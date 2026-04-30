#--- Dataframe of dust events and the 30 days of moisture before and after
#--- Add dask dataframe or run through xarray, currently doesn't have parallel (runs in 5 min)

import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime
from dask.distributed import Client
import time
from pathlib import Path

def main(): 
    start = time.time()

    with Client(dashboard_address="127.0.0.1:8787") as client:
        print(client)

        location_name = "American Southwest"
        dust_path = "DATA/raw/line_dust/dust_dataset_final_20241226.txt"
        dust_df = get_dust_df(dust_path)

        #--- extend to 30 days before and after
        dfs = []
        for d in range(-30, 31):
            temp = dust_df.copy()
            temp["datetime"] = temp["datetime"] + pd.Timedelta(days=d)
            if d == -30:
                temp["is_start"] = "Y"
            if d == 0:
                temp["is_dust_event"] = "Y"
            dfs.append(temp)
        df_expanded = pd.concat(dfs, ignore_index=True)
        df_expanded = df_expanded.sort_values(by="datetime")
        df_expanded = df_expanded.reset_index()

        #--- moisture data
        processed_moisture_path = Path("DATA/processed/1_moisture_grid_2026-04-23.nc")
        df_expanded = add_moisture_to_dust_df(processed_moisture_path, df_expanded)

        #--- save dataset
        timestamp = datetime.today().strftime("%Y-%m-%d")
        df_expanded.to_csv(f"DATA/processed/6_time_trend_{timestamp}.csv", index=False)
        
    end = time.time()
    print(f"Time to process: {end - start:.2f} seconds")

    return

#------------------------

def read_dust_data_into_df(dust_path):
    
    dust_df = pd.read_csv(dust_path, sep=r'\s+', skiprows=2, header=None)
    dust_df.columns = ['Date (YYYYMMDD)', 'start time (UTC)', 'latitude', 'longitude', 'Jesse check']

    #--- Clean lat/lon data
    dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
    dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')
    dust_df = dust_df.dropna(subset=['latitude', 'longitude'])

    return dust_df

def get_dust_df(dust_path):
    print("Opening dust data, creating dust dataframe... ")
    dust_df = read_dust_data_into_df(dust_path)

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

def add_moisture_to_dust_df(path_moisture_grid_dust_days, dust_df):

    print(f"Loading cached wldas data from {path_moisture_grid_dust_days}")
        #--- Seems to have some good default chunking scheme, 
        #--- gives me a warning when I try to implement my own
    moisture_dust_days = xr.open_dataset(path_moisture_grid_dust_days)

    print("Adding WLDAS moisture to dust dataframe...")

    moisture_dates = pd.to_datetime(moisture_dust_days.time.values).normalize()
    moisture_dates_set = set(moisture_dates.values)

    dust_df['moisture'] = None
    skipped_no_wldas_date = 0

    for idx, row in dust_df.iterrows():
        dust_time = row['datetime'].normalize()

        if dust_time.to_datetime64() not in moisture_dates_set:
            skipped_no_wldas_date += 1
            continue

        try:
            wldas_point = moisture_dust_days.sel(
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