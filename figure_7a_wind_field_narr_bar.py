import xarray as xr
import numpy as np
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from modules_soil_orders import soil_orders_utils as soil_orders
from modules_line_dust import line_dust_utils as dust

#--- Data from NARR
#------ Just 2001 so far!
print("Opening data from NARR...")

ds_uwnd = xr.open_dataset("/mnt/data2/jturner/narr/uwnd.10m.2001.nc")
ds_vwnd = xr.open_dataset("/mnt/data2/jturner/narr/vwnd.10m.2001.nc")

#--- Creating or loading wind speed data

cache_path = Path("/mnt/data2/jturner/narr/processed/narr_wind_speed.nc")
if cache_path.exists():
    print("Loading cached wind speed...")
    ds_ws = xr.open_dataset(cache_path)
else:
    print("Computing wind speed and saving to cache...")
    ds = xr.merge([ds_uwnd, ds_vwnd])
    ds_ws = xr.Dataset(
        {"wind_speed": np.sqrt(ds["uwnd"]**2 + ds["vwnd"]**2)},
        coords=ds.coords,
        attrs=ds.attrs)
    ds_ws = ds_ws.chunk({"time": 24})
    ds_ws.to_netcdf(cache_path)

#--- Cropping to American Southwest
print("Cropping to American Southwest...")
min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region(
    "American Southwest")

lat = ds_ws["lat"]
lon = ds_ws["lon"]

mask = (
    (lat >= min_lat) & (lat <= max_lat) &
    (lon >= min_lon) & (lon <= max_lon))

ds_ws = ds_ws.where(mask, drop=True)

#--- Total wind field climatology

all_winds = ds_ws["wind_speed"].values.flatten()
all_winds = all_winds[~np.isnan(all_winds)]

#--- Open dust data, create datetime column
print("Opening dust data, creating dust dataframe... ")

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
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

#--- Temporary time filter to 2001
print("Temporarily filtering to 2001 only...")
dust_df = dust_df[
    dust_df["datetime"].dt.year == 2001
].copy()

#--- Spatial matching of wind grid (Lambert Conformal)
print("Spatial matching of wind grid...")

def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

lat2d = ds_ws["lat"].values
lon2d = ds_ws["lon"].values

#--- Extract wind speeds at dust events
print("Extracting wind speeds at dust events...")

dust_winds = []

for _, row in dust_df.iterrows():
    iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
    
    # nearest-time match
    ws = ds_ws["wind_speed"].sel(
        time=row["datetime"],
        method="nearest"
    ).isel(y=iy, x=ix)
    
    dust_winds.append(ws.item())

dust_winds = np.array(dust_winds)
dust_winds = dust_winds[~np.isnan(dust_winds)]

#--- Create bins for distributions
print("Creating bins for distributions...")

bins = np.linspace(
    min(all_winds.min(), dust_winds.min()),
    max(all_winds.max(), dust_winds.max()),
    30  # number of bins
)

hist_all, _ = np.histogram(all_winds, bins=bins)
hist_dust, _ = np.histogram(dust_winds, bins=bins)

hist_all = hist_all / hist_all.sum()
hist_dust = hist_dust / hist_dust.sum()

#--- Create counts dataframe
print("Creating counts dataframe...")
bin_centers = 0.5 * (bins[:-1] + bins[1:])
bin_labels = [f"{bins[i]:.1f}–{bins[i+1]:.1f}" for i in range(len(bins) - 1)]

counts_df = pd.DataFrame(
    {
        "Dust points": hist_dust,
        "Full domain": hist_all,
    },
    index=bin_labels
)

#--- Plot bar chart
print("Plotting bar chart...")

fig_bar, ax_bar = plt.subplots(figsize=(12, 6))

x = np.arange(len(counts_df))
width = 0.35

for i, bin_label in enumerate(counts_df.index):
    ax_bar.bar(
        x[i] - width / 2,
        counts_df.loc[bin_label, "Dust points"],
        width,
        color="tab:orange",
        edgecolor="black",
        linewidth=1,
        label="Dust events" if i == 0 else ""
    )

    ax_bar.bar(
        x[i] + width / 2,
        counts_df.loc[bin_label, "Full domain"],
        width,
        color="tab:blue",
        alpha=0.5,
        label="Full domain" if i == 0 else ""
    )

ax_bar.set_xticks(x)
ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
ax_bar.set_ylabel("Fraction of total")
ax_bar.set_xlabel("Wind speed (m/s)")
ax_bar.set_title("NARR Wind Speed Distribution: Dust Events vs Full Domain")

ax_bar.legend()
plt.tight_layout()

soil_orders._plot_save(
    fig_bar,
    plot_dir="figures",
    plot_name="narr_wind_speed_bar_chart"
)
