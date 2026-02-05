from modules_soil_moisture import utils_processing as wldas_proc
from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as soil_orders

from pathlib import Path
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths for cached datasets
processed_ds_total_path = Path("data/processed/wldas_sample/wldas_total.nc")
processed_ds_dust_path = Path("data/processed/wldas_sample/wldas_dust.nc")

print("Checking for cached WLDAS datasets...")
if processed_ds_total_path.exists():
    print(f"Loading cached wldas_total from {processed_ds_total_path}")
    wldas_total = xr.open_dataset(processed_ds_total_path)
else:
    wldas_total = None

if processed_ds_dust_path.exists():
    print(f"Loading cached wldas_dust from {processed_ds_dust_path}")
    wldas_dust = xr.open_dataset(processed_ds_dust_path)
else:
    wldas_dust = None

print("Opening dust dataset...")
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

if wldas_total is None:
    print("Opening WLDAS files for each dust date...")

    wldas_path = "/mnt/data2/jturner/wldas_data"
    wldas_files = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['Date (YYYYMMDD)'].astype(str)
    ]

    num_wldas_files = 120
    print(f"Only opening first {num_wldas_files} WLDAS files...")
    wldas_total = wldas_proc.open_wldas_files_as_xarray_ds(wldas_files[:num_wldas_files])
else:
    print("Using cached wldas_total")


#--- Filter not doing anything right now, maybe sample is sufficient
# ds_total = wldas_proc.filter_by_bounds(ds_total, location_name="American Southwest")

if wldas_dust is None:
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
else:
    print("Using cached wldas_dust")


print("Saving processed files as NetCDFs...")
processed_ds_total_path.parent.mkdir(parents=True, exist_ok=True)

#--- Coarsen resolution for wldas_total
COARSEN_LAT = 24
COARSEN_LON = 24
wldas_total = (
    wldas_total
    .coarsen(lat=COARSEN_LAT, lon=COARSEN_LON, boundary="trim")
    .mean()
)

if not processed_ds_total_path.exists():
    wldas_total.to_netcdf(processed_ds_total_path)
    print(f"Saved wldas_total → {processed_ds_total_path}")

if not processed_ds_dust_path.exists():
    wldas_dust.to_netcdf(processed_ds_dust_path)
    print(f"Saved wldas_dust → {processed_ds_dust_path}")

#--- Define bins
bins = np.linspace(0, 0.5, 21)  # 0.0, 0.05, ..., 0.5
bin_labels = [f"{round(bins[i],2)}-{round(bins[i+1],2)}" for i in range(len(bins)-1)]

print("Flatten data and remove NaNs...")
wldas_total = wldas_total['SoilMoi00_10cm_tavg'].values.flatten()
wldas_total = wldas_total[~np.isnan(wldas_total)]
wldas_dust = wldas_dust['SoilMoi00_10cm_tavg'].values.flatten()
wldas_dust = wldas_dust[~np.isnan(wldas_dust)]

print("Compute histogram counts...")
counts_total, _ = np.histogram(wldas_total, bins=bins)
counts_dust, _ = np.histogram(wldas_dust, bins=bins)

fraction_total = counts_total / counts_total.sum()
fraction_dust = counts_dust / counts_dust.sum()

print("Prepare dataframe for plotting...")
counts_df = pd.DataFrame({
    "Full domain": fraction_total,
    "Dust regions": fraction_dust
}, index=bin_labels)

print("Plotting bar chart...")
fig_bar, ax_bar = plt.subplots(figsize=(12, 6))
x = np.arange(len(counts_df))
width = 0.35

for i, bin_label in enumerate(counts_df.index):
    ax_bar.bar(
        x[i] - width / 2, counts_df.loc[bin_label, "Dust regions"],
        width, color="tab:orange", edgecolor="black", linewidth=1,
        label="Dust regions" if i == 0 else ""
    )
    ax_bar.bar(
        x[i] + width / 2, counts_df.loc[bin_label, "Full domain"],
        width, color="tab:blue", alpha=0.5,
        label="Full domain" if i == 0 else ""
    )

ax_bar.set_xticks(x)
ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
ax_bar.set_ylabel("Fraction of total")
ax_bar.set_xlabel("Soil Moisture (0-10 cm) [m³/m³]")
ax_bar.set_title("Soil Moisture Distribution: Dust Regions vs Full Domain")
ax_bar.legend()

soil_orders._plot_save( fig_bar, plot_dir="figures", plot_name="soil_moisture_bar_chart" )
