from modules_soil_moisture import utils_processing as wldas_proc
from modules_line_dust import line_dust_utils as dust

from pathlib import Path
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Paths for cached datasets
    processed_wldas_path = Path("data/processed/wldas_sample")
    wldas_path = "/mnt/data2/jturner/wldas_data"

    #--- Option to re-run the cached moisture datasets
    rerun_moisture_data = False

    print("Opening dust dataset...")
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)

    if rerun_moisture_data:
        wldas_total = create_wldas_total(wldas_path, dust_df)
        wldas_dust = create_wldas_dust(wldas_total, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total, wldas_dust)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        wldas_total = xr.open_dataset(processed_wldas_path / "wldas_total.nc")
        wldas_dust = xr.open_dataset(processed_wldas_path / "wldas_dust.nc")

    import figure_5a_moisture_bar as fig_5a
    fig_5a.plot_bar_chart_moisture(wldas_total, wldas_dust)
    
    return

#------------------------

def create_wldas_total(wldas_path, dust_df):
    print("Opening WLDAS files for each dust date...")
    
    wldas_files = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['Date (YYYYMMDD)'].astype(str)
    ]

    num_wldas_files = 20
    print(f"Only opening first {num_wldas_files} WLDAS files...")
    wldas_total = wldas_proc.open_wldas_files_as_xarray_ds(wldas_files[:num_wldas_files])
    return wldas_total

def create_wldas_dust(wldas_total, dust_df):
    print("Create dust WLDAS dataset...")

    dust_df['datetime'] = pd.to_datetime(
        dust_df['Date (YYYYMMDD)'].astype(str),
        format="%Y%m%d"
    )

    wldas_dates = pd.to_datetime(wldas_total.time.values).normalize()
    wldas_dates_set = set(wldas_dates.values)

    wldas_points = []
    skipped_no_wldas_date = 0

    for idx, row in dust_df.iterrows():
        dust_time = row['datetime'].normalize()

        if dust_time.to_datetime64() not in wldas_dates_set:
            skipped_no_wldas_date += 1
            continue

        try:
            wldas_point = wldas_total.sel(
                time=dust_time,
                lat=row['latitude'],
                lon=row['longitude'],
                method="nearest"
            )

            wldas_point = wldas_point.assign_coords(dust_index=idx)
            wldas_points.append(wldas_point)

        except KeyError as e:
            print(f"Skipping row {idx}: {e}")

    wldas_dust = xr.concat(wldas_points, dim="dust_index")

    print(f"Total dust points: {len(dust_df)}")
    print(f"Skipped (no matching WLDAS date): {skipped_no_wldas_date}")
    print(f"Dust points tracked: {len(wldas_dust.dust_index)}")

    return wldas_dust

def saving_processed_files(processed_wldas_path, wldas_total, wldas_dust):
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

    wldas_dust.to_netcdf(processed_wldas_path / "wldas_dust_18.nc")
    print(f"Saved wldas_dust → {processed_wldas_path}")

    return

#------------------

if __name__ == "__main__":
    main()