from modules_soil_moisture import utils_processing as wldas_proc
from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as soil_orders

from pathlib import Path
import random
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ds = None
ds_dust_ever = None

# Paths for cached datasets
processed_ds_path = Path("data/processed/wldas_sample/wldas_ds.nc")
processed_ds_dust_path = Path("data/processed/wldas_sample/wldas_ds_dust_ever.nc")

ds = None
ds_dust_ever = None

if processed_ds_path.exists() and processed_ds_dust_path.exists():
    print("Loading cached WLDAS datasets...")
    ds = xr.open_dataset(processed_ds_path)
    ds_dust_ever = xr.open_dataset(processed_ds_dust_path)

else:
    print("Cached dataset not found — creating it...")

    #--- Sample the WLDAS data
    wldas_path = "/mnt/data2/jturner/wldas_data"
    file_dir = Path(wldas_path)
    file_sample = random.sample(list(file_dir.glob("*.nc4")), 60)

    print("Load files in xarray dataset...")
    ds = wldas_proc.open_wldas_files_as_xarray_ds(file_sample)
    ds = wldas_proc.filter_by_bounds(ds, location_name="American Southwest")

    print("Filter moisture dataset to dust-producing regions...")
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    ds_dust_ever = wldas_proc.filter_by_ever_dust_points(ds, dust_df)

    # Save both datasets for next time
    processed_ds_path.parent.mkdir(parents=True, exist_ok=True)

    print("Saving files as netcdfs...")
    print("--- Skipping this step, it is too annoying and slow ---")
    # INSERT SAVE HERE, WHEN INSPIRED
    # MIGHT NEED A COARSEN STEP


var_name = "SoilMoi00_10cm_tavg"

#--- Define bins
bins = np.linspace(0, 0.5, 11)  # 0.0, 0.05, ..., 0.5
bin_labels = [f"{round(bins[i],2)}-{round(bins[i+1],2)}" for i in range(len(bins)-1)]

print("Flatten data and remove NaNs...")
ds_tot = ds[var_name].values.flatten()
ds_tot = ds_tot[~np.isnan(ds_tot)]
ds_dust = ds_dust_ever[var_name].values.flatten()
ds_dust = ds_dust[~np.isnan(ds_dust)]

print("Compute histogram counts...")
counts_tot, _ = np.histogram(ds_tot, bins=bins)
counts_dust, _ = np.histogram(ds_dust, bins=bins)

fraction_tot = counts_tot / counts_tot.sum()
fraction_dust = counts_dust / counts_dust.sum()

print("Prepare dataframe for plotting...")
counts_df = pd.DataFrame({
    "Full domain": fraction_tot,
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
