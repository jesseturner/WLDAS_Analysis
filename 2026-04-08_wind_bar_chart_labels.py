#--- This version of the bar chart adds lines for the population medians 
#--- and a label for the number of points. 

from pathlib import Path
import xarray as xr
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

from modules_line_dust import line_dust_utils as dust

def main():
    ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
    wind_speed_ds = get_wind_speed_ds(ws_data_path)    

    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    ws_currently_blowing, ws_anytime = get_wind_speed_at_dust_origins(wind_speed_ds, dust_df)

    print("\n WS currently blowing \n", np.shape(ws_currently_blowing))

    print("\n WS anytime \n", np.shape(ws_anytime))

    counts_df = hist_bins_and_counts(ws_currently_blowing, ws_anytime)

    medians = get_medians(ws_currently_blowing, ws_anytime)

    counts = ws_currently_blowing.size, ws_anytime.size

    plot_bar_chart(counts_df, medians, counts)

    return

#------------------------

def get_wind_speed_ds(ws_data_path):
    if ws_data_path.exists():
        print("Loading wind speed data...")
        #--- Chunking makes a huge difference with speed
        ds_ws = xr.open_dataset(ws_data_path, chunks={"time": 100})
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()

    return ds_ws

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

def get_wind_speed_at_dust_origins(wind_speed_ds, dust_df):

    y_indices, x_indices, time_indices = match_dust_and_wind_speed_grids(wind_speed_ds, dust_df)

    ws_currently_blowing = []
    ws_anytime = []

    print("Extracting wind speeds at dust events and for whole time range...")

    #--- Day-of time match 
    ws_currently_blowing = wind_speed_ds["wind_speed"].isel(
        y=xr.DataArray(y_indices, dims="points"),
        x=xr.DataArray(x_indices, dims="points"),
        time=xr.DataArray(time_indices, dims="points")
    )

    #--- Full time domain match 
    ws_anytime = wind_speed_ds["wind_speed"].isel(
        y=xr.DataArray(y_indices, dims="points"),
        x=xr.DataArray(x_indices, dims="points"),
    )
    
    return ws_currently_blowing, ws_anytime

def nearest_grid_point(ws_lat2d, ws_lon2d, dust_lat, dust_lon):
    dist2 = (ws_lat2d - dust_lat)**2 + (ws_lon2d - dust_lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

def match_dust_and_wind_speed_grids(wind_speed_ds, dust_df):
    print("Spatial matching of wind grid (Lambert Conformal)...")

    lat2d = wind_speed_ds["lat"].values
    lon2d = wind_speed_ds["lon"].values

    y_indices = []
    x_indices = []
    time_indices = []
    
    time_index = wind_speed_ds["time"].to_index()

    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        y_indices.append(iy.item())
        x_indices.append(ix.item())

        #--- Get datatime index
        t = row["datetime"].floor("D")
        it = time_index.get_indexer([t], method="nearest")[0]
        time_indices.append(it)

    return y_indices, x_indices, time_indices

def hist_bins_and_counts(ws_currently_blowing, ws_anytime):

    bins = np.linspace(ws_anytime.min().compute().item(), ws_anytime.max().compute().item(), 30)

    hist_all, _ = np.histogram(ws_anytime, bins=bins)
    hist_dust, _ = np.histogram(ws_currently_blowing, bins=bins)

    #--- Normalizing the histograms
    hist_all = hist_all / hist_all.sum()
    hist_dust = hist_dust / hist_dust.sum()

    print("Creating counts dataframe...")
    bin_centers = 0.5 * (bins[:-1] + bins[1:])
    bin_labels = [f"{bins[i]:.1f}-{bins[i+1]:.1f}" for i in range(len(bins) - 1)]

    counts_df = pd.DataFrame(
        {
            "Wind speed (currently blowing)": hist_dust,
            "Wind speed (anytime)": hist_all,
        },
        index=bin_labels
    )

    return counts_df

def get_medians(ws_currently_blowing, ws_anytime):
    median_anytime = ws_anytime.compute().median(skipna=True).values
    median_currently_blowing = ws_currently_blowing.compute().median(skipna=True).values

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
            counts_df.loc[bin_label, "Wind speed (currently blowing)"],
            width,
            color="tab:orange",
            edgecolor="black",
            linewidth=1,
            label=f"Wind speed (current dust event) \n n={counts[0]:.2e}" if i == 0 else ""
        )

        ax_bar.bar(
            x[i] + width / 2,
            counts_df.loc[bin_label, "Wind speed (anytime)"],
            width,
            color="tab:blue",
            alpha=0.5,
            label=f"Wind speed (anytime) \n n={counts[1]:.2e}" if i == 0 else ""
        )

    add_medians_to_plot(ax_bar, medians)

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
    ax_bar.set_ylabel("Fraction of total", fontsize=18)
    ax_bar.set_xlabel("Wind speed (m/s)", fontsize=18)
    ax_bar.set_title("NARR Wind Speed Distribution at Dust Origin Sites", fontsize=24, pad=12)

    ax_bar.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("figures", "wind_speed_bar_chart"), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

def add_medians_to_plot(ax_bar, medians):
    ax_bar.axvline(
        medians[0],
        color="tab:orange",
        linestyle="--",
        linewidth=2,
        zorder=0
    )
    ax_bar.text(x=medians[0], 
                y=0.8,
                s=f'Median: {medians[0]:.1f} m/s', 
                color="tab:orange",
                alpha=0.8, 
                fontsize=10,
                fontweight='bold',
                rotation=90,
                verticalalignment='center',
                horizontalalignment='right',
                transform=ax_bar.get_xaxis_transform())

    ax_bar.axvline(
        medians[1],
        color="tab:blue",
        linestyle="--",
        linewidth=2,
        zorder=0
    )

    ax_bar.text(x=medians[1], 
                y=0.8,
                s=f'Median: {medians[1]:.1f} m/s', 
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