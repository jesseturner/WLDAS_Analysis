import pandas as pd
import xarray as xr
from pathlib import Path
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import sys

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as soil_orders

ws_data_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")
if ws_data_path.exists():
    print("Loading wind speed data...")
    ds_ws = xr.open_dataset(ws_data_path)
else:
    print("Wind speed data not found, exiting...")
    sys.exit()

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


print("Temporarily filtering to 2001 only...")
dust_df = dust_df[
    dust_df["datetime"].dt.year.isin([2001])
].copy()

#--- Find datetime with most dust reports
print("Finding dustiest datetime...")

dust_counts = (
    dust_df
    .groupby("datetime")
    .size()
    .sort_values(ascending=False)
)

#--- Set the target date from the list of most dust events
rank_dust_event = 0
target_time = dust_counts.index[rank_dust_event]
print(f"Plotting dust event ranked: {rank_dust_event}")
print(f"Selected datetime: {target_time} ({dust_counts.iloc[rank_dust_event]} dust points)")

dust_t = dust_df[dust_df["datetime"] == target_time]

#--- Select wind at target time
#------ Getting day of with "floor", then going to 12 UTC because "daytime winds" uses that time for whole day
ws_t = ds_ws["wind_speed"].sel(time=target_time.floor("D") + pd.Timedelta(hours=12)) 
print(f"Using NARR time of {ws_t.time.values}...")

lat2d = ws_t["lat"].values
lon2d = ws_t["lon"].values

#--- Plotting map
print("Plotting wind field and dust points...")

proj = ccrs.LambertConformal(
    central_longitude=-100,
    central_latitude=35
)

fig = plt.figure(figsize=(12, 10))
ax = plt.axes(projection=proj)

ax.add_feature(cfeature.STATES, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=0.8)
ax.coastlines(resolution="50m", linewidth=0.8)

pcm = ax.pcolormesh(
    lon2d,
    lat2d,
    ws_t,
    transform=ccrs.PlateCarree(),
    cmap="viridis",
    shading="auto"
)

cbar = plt.colorbar(pcm, ax=ax, pad=0.02)
cbar.set_label("Wind speed (m/s)")

#--- Dust points
ax.scatter(
    dust_t["longitude"],
    dust_t["latitude"],
    s=40,
    color="red",
    edgecolor="black",
    linewidth=0.5,
    transform=ccrs.PlateCarree(),
    label=f"Dust reports (n={len(dust_t)})"
)

ax.legend(loc="upper right")

ax.set_title(
    f"NARR 10 m Wind Field and Dust Reports\n{target_time}",
    fontsize=14
)

plt.tight_layout()

soil_orders._plot_save(
    fig,
    plot_dir="figures",
    plot_name=f"narr_wind_dust_{target_time:%Y%m%d_%H%M}"
)
