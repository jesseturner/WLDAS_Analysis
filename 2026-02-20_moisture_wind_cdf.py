from pathlib import Path
import xarray as xr
import sys
import rioxarray as rxr
import numpy as np
import os
import pandas as pd
import matplotlib.pyplot as plt

from modules_line_dust import line_dust_utils as dust

def main():

    dust_df = open_dust_dataset()
    dust_df = add_wind_speed_data_to_dust_df(dust_df)

    # Paths for cached datasets
    processed_wldas_path = Path("data/processed/wldas_sample/wldas_total_2026_02_18.nc")
    wldas_path = "/mnt/data2/jturner/wldas_data"

    #--- Option to re-run the cached moisture datasets
    rerun_moisture_data = False

    if rerun_moisture_data:
        print("--- Rerunning WLDAS processing into xarray datasets ---")
        wldas_total = create_wldas_total(wldas_path, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        wldas_total = xr.open_dataset(processed_wldas_path)

    dust_df = add_wldas_moisture_to_dust_df(wldas_total, dust_df)
    dust_df_sorted, column_name, moisture_labels, colors, save_name = moisture_info_for_cdf(dust_df)
    plot_cdf(dust_df_sorted, column_name, moisture_labels, colors, save_name)


    return

#------------------------

def open_dust_dataset():
    #--- DUST DATA
    print("Opening dust dataset...")
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name=location_name)
    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"],
        format="%Y%m%d"
    )
    return dust_df

def add_wind_speed_data_to_dust_df(dust_df):
    #--- WIND SPEED DATA
    ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
    if ws_data_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(ws_data_path)
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
            time=row["datetime"].floor("D"),
            method="nearest"
        ).isel(y=iy, x=ix)
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds
    dust_df = dust_df.dropna(subset=["wind_speed"])
    return dust_df

def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

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

    wldas_total.to_netcdf(processed_wldas_path)
    print(f"Saved wldas_total → {processed_wldas_path}")

    return

def add_wldas_moisture_to_dust_df(wldas_total, dust_df):
    print("Adding WLDAS moisture to dust dataframe...")

    wldas_dates = pd.to_datetime(wldas_total.time.values).normalize()
    wldas_dates_set = set(wldas_dates.values)

    dust_df['moisture'] = None
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
            )['SoilMoi00_10cm_tavg'].values.item()

            dust_df.at[idx, 'moisture'] = wldas_point

        except KeyError as e:
            print(f"Skipping row {idx}: {e}")

    print(f"Total dust points: {len(dust_df)}")
    print(f"Skipped (no matching WLDAS date): {skipped_no_wldas_date}")
    print(f"Dust points tracked: {dust_df['moisture'].notna().sum()}")

    return dust_df

def moisture_info_for_cdf(dust_df):
    print("Making moisture categories...")
    moisture_bins = [0.00, 0.05, 0.10, 0.15, 0.20, 0.25]
    moisture_labels = ["0.00-0.05", "0.05-0.10", "0.10-0.15", "0.15-0.20", "0.20-0.25"]
    dust_df["moisture"] = pd.to_numeric(dust_df["moisture"], errors="coerce")
    dust_df["moisture_category"] = pd.cut(
        dust_df["moisture"],
        bins=moisture_bins,
        labels=moisture_labels,
        include_lowest=True
    )
    dust_df_filtered = dust_df.dropna(subset=["moisture_category"])

    colors = [
        "#8c510a",  # Extremely Dry – dark soil brown
        "#bf812d",  # Very Dry – warm earth
        "#dfc27d",  # Dry – tan soil
        "#80cdc1",  # Slightly Moist – muted teal
        "#35978f",  # Moist – strong teal
    ]
    save_name = "wind_moisture_cdf.png"
    column_name = "moisture_category"
    
    print("Building and plotting the order cumulative distribution function...")
    #freq of dust = blowing per domain / domain count
    dust_df_sorted = dust_df_filtered.sort_values(['moisture_category', 'wind_speed'])
    dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('moisture_category', observed=False).cumcount() + 1
    dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('moisture_category', observed=False)['cum_pct'].transform('max') * 100
    return dust_df_sorted, column_name, moisture_labels, colors, save_name

def plot_cdf(dust_df_sorted, column_name, selected_list, colors, save_name):

    fig, ax = plt.subplots(figsize=(15, 6))

    for i, category in enumerate(selected_list):
        subset = dust_df_sorted[dust_df_sorted[column_name] == category]
        ax.step(subset['wind_speed'], subset['cum_pct'], where='post', 
                label=selected_list[i],
                color=colors[i], 
                linewidth=3)

    ax.set_xlim(0, 20)
    ax.set_xlabel('Wind Speed (m/s)', size=15)
    ax.set_ylabel('Cumulative Percentage (%)', size=15)
    ax.set_title('Dust events by wind speed and moisture', size=18)
    ax.tick_params(axis='both', which='major', labelsize=15) 
    ax.legend(fontsize=15, title="Soil Moisture \n (0-10 cm) [m³/m³]", title_fontsize=15)

    plt.tight_layout()
    plt.savefig(os.path.join("figures", save_name), bbox_inches='tight', dpi=300)
    plt.close(fig)
    return

#------------------------

if __name__ == "__main__":
    main()