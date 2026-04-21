#--- NetCDF file with WLDAS soil moisture (coarsened) for each dust day

from pathlib import Path
import xarray as xr
import pandas as pd
from datetime import datetime

def main():
    #--- Get dust days
    dust_path = "DATA/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    #--- Get moisture for each dust day
    wldas_path = "/mnt/data2/jturner/wldas_data"
    moisture_grid_dust_days = create_moisture_grid_dust_days(wldas_path, dust_df)

    #--- save coarsened dataset
    timestamp = datetime.today().strftime("%Y-%m-%d")
    saving_processed_files(f"DATA/processed/2_moisture_grid_dust_days_{timestamp}", moisture_grid_dust_days)

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

def create_moisture_grid_dust_days(wldas_path, dust_df):
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

#------------------------

if __name__ == "__main__":
    main()