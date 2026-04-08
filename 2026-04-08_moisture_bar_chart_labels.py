#--- This version of the bar chart adds lines for the population medians 
#--- and a label for the number of points. 

from pathlib import Path
import xarray as xr
import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt

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

    print("\n Moisture currently blowing \n", np.shape(moist_currently_blowing))

    print("\n Moisture anytime \n", np.shape(moist_anytime))

    counts_df = hist_bins_and_counts(moist_currently_blowing, moist_anytime)

    medians = get_medians(moist_currently_blowing, moist_anytime)

    counts = moist_currently_blowing.size, moist_anytime.size

    plot_bar_chart(counts_df, medians, counts)

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

def hist_bins_and_counts(moist_currently_blowing, moist_anytime):

    bins = np.linspace(moist_anytime.min().compute().item(), moist_anytime.max().compute().item(), 30)

    hist_all, _ = np.histogram(moist_anytime, bins=bins)
    hist_dust, _ = np.histogram(moist_currently_blowing, bins=bins)

    #--- Normalizing the histograms
    hist_all = hist_all / hist_all.sum()
    hist_dust = hist_dust / hist_dust.sum()

    print("Creating counts dataframe...")
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    bin_labels = [f"{bins[i]:.2f}-{bins[i+1]:.2f}" for i in range(len(bins) - 1)]

    counts_df = pd.DataFrame(
        {
            "Moisture (currently blowing)": hist_dust,
            "Moisture (anytime)": hist_all,
        },
        index=bin_labels
    )

    return counts_df

def get_medians(moist_currently_blowing, moist_anytime):
    median_anytime = moist_anytime.compute().median(skipna=True).values
    median_currently_blowing = moist_currently_blowing.compute().median(skipna=True).values

    medians = median_currently_blowing, median_anytime

    return medians

def plot_bar_chart(counts_df, medians, counts):
    print("Plotting bar chart...")

    fig, ax_bar = plt.subplots(figsize=(12, 6))

    x = np.arange(len(counts_df))
    width = 0.35

    for i, bin_label in enumerate(counts_df.index):
        ax_bar.bar(
            x[i] - width / 2,
            counts_df.loc[bin_label, "Moisture (currently blowing)"],
            width,
            color="tab:orange",
            edgecolor="black",
            linewidth=1,
            label=f"Moisture (current dust event) \n n={counts[0]:.2e}" if i == 0 else ""
        )

        ax_bar.bar(
            x[i] + width / 2,
            counts_df.loc[bin_label, "Moisture (anytime)"],
            width,
            color="tab:blue",
            alpha=0.5,
            label=f"Moisture (anytime) \n n={counts[1]:.2e}" if i == 0 else ""
        )

    add_medians_to_plot(ax_bar, medians)

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
    ax_bar.set_ylabel("Fraction of total", fontsize=18)
    ax_bar.set_xlabel("Soil Moisture (0-10 cm) [m³/m³]", fontsize=18)
    ax_bar.set_title("Soil Moisture Distribution at Dust Origin Sites", fontsize=24)

    ax_bar.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("figures", "moisture_bar_chart"), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

def add_medians_to_plot(ax_bar, medians):

    #--- This is a terrible thing to do
    #--- These numbers are based on the range of values (0-.42) and number of columns (28)
    adjustment = (1/.42) * 28

    ax_bar.axvline(
        medians[0]*adjustment,
        color="tab:orange",
        linestyle="--",
        linewidth=2,
        zorder=0
    )
    ax_bar.text(x=medians[0]*adjustment, 
                y=0.93,
                s=f'{medians[0]:.2f}', 
                color="tab:orange",
                alpha=0.8, 
                fontsize=10,
                fontweight='bold',
                rotation=90,
                verticalalignment='center',
                horizontalalignment='right',
                transform=ax_bar.get_xaxis_transform())

    ax_bar.axvline(
        medians[1]*adjustment,
        color="tab:blue",
        linestyle="--",
        linewidth=2,
        zorder=0
    )
    
    ax_bar.text(x=medians[1]*adjustment, 
                y=0.93,
                s=f'{medians[1]:.2f}', 
                color="tab:blue",
                alpha=0.8, 
                fontsize=10,
                fontweight='bold',
                rotation=90,
                verticalalignment='center',
                horizontalalignment='right',
                transform=ax_bar.get_xaxis_transform())
    
    return

#------------------------

if __name__ == "__main__":
    main()