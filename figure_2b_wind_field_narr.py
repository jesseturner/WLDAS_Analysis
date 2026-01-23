import pandas as pd
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as soil_orders

#--- Data from NARR
#------ Just 2001 so far!
print("Opening data from NARR...")

ds_uwnd = xr.open_dataset("/mnt/data2/jturner/narr/uwnd.10m.2001.nc")
ds_vwnd = xr.open_dataset("/mnt/data2/jturner/narr/vwnd.10m.2001.nc")

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

#--- Find datetime with most dust reports
print("Finding dustiest datetime...")

dust_counts = (
    dust_df
    .groupby("datetime")
    .size()
    .sort_values(ascending=False)
)

target_time = dust_counts.index[0]
print(f"Selected datetime: {target_time} ({dust_counts.iloc[0]} dust points)")

dust_t = dust_df[dust_df["datetime"] == target_time]

#--- Select wind at target time
uwnd_t = ds_uwnd["uwnd"].sel(time=target_time, method="nearest")
vwnd_t = ds_vwnd["vwnd"].sel(time=target_time, method="nearest")

wind_speed_t = np.sqrt(uwnd_t**2 + vwnd_t**2)

#--- Crop to American Southwest

lat = ds_uwnd["lat"]
lon = ds_uwnd["lon"]

min_lat, max_lat, min_lon, max_lon = soil_orders._get_coords_for_region(
    "American Southwest")

mask = (
    (lat >= min_lat) & (lat <= max_lat) &
    (lon >= min_lon) & (lon <= max_lon)
)

uwnd_t = uwnd_t.where(mask, drop=True)
vwnd_t = vwnd_t.where(mask, drop=True)
wind_speed_t = wind_speed_t.where(mask, drop=True)

lat2d = uwnd_t["lat"].values
lon2d = uwnd_t["lon"].values


#--- Plotting map
print("Plotting wind field and dust points...")

proj = ccrs.LambertConformal(
    central_longitude=-100,
    central_latitude=35
)

fig = plt.figure(figsize=(12, 10))
ax = plt.axes(projection=proj)

# --- Map extent (lon/lat)
ax.set_extent(
    [min_lon, max_lon, min_lat, max_lat],
    crs=ccrs.PlateCarree()
)

# --- Background features
ax.add_feature(cfeature.STATES, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=0.8)
ax.coastlines(resolution="50m", linewidth=0.8)

# --- Wind speed shading
pcm = ax.pcolormesh(
    lon2d,
    lat2d,
    wind_speed_t,
    transform=ccrs.PlateCarree(),
    cmap="viridis",
    shading="auto"
)

cbar = plt.colorbar(pcm, ax=ax, pad=0.02)
cbar.set_label("Wind speed (m/s)")

# --- Wind vectors (thinned so it’s readable)
skip = 5
ax.quiver(
    lon2d[::skip, ::skip],
    lat2d[::skip, ::skip],
    uwnd_t.values[::skip, ::skip],
    vwnd_t.values[::skip, ::skip],
    transform=ccrs.PlateCarree(),
    scale=400,
    width=0.002
)

# --- Dust points
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
