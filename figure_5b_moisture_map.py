from modules_soil_orders import soil_orders_utils as soil_orders

from pathlib import Path
import xarray as xr
import sys
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt


# Paths for cached datasets
processed_wldas_total_path = Path("data/processed/wldas_sample/wldas_total.nc")
processed_wldas_dust_path = Path("data/processed/wldas_sample/wldas_dust.nc")

print("Getting cached WLDAS datasets...")
if processed_wldas_total_path.exists() and processed_wldas_dust_path.exists():
    wldas_total = xr.open_dataset(processed_wldas_total_path)
    wldas_dust = xr.open_dataset(processed_wldas_dust_path)
else:
    print("Missing a cached file, run figure_5a to create them.")
    sys.exit()

print("Finding the day with most dust events...")
dust_times = pd.to_datetime(wldas_dust.time.values)

dust_counts_by_day = (
    pd.Series(dust_times)
    .dt.normalize()
    .value_counts()
    .sort_values(ascending=False)
)

peak_dust_day = dust_counts_by_day.index[0]

print("Plotting WLDAS scene with dust events...")

wldas_scene = wldas_total.sel(time=peak_dust_day)

fig = plt.figure(figsize=(12, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# --- Plot WLDAS soil moisture
sm = wldas_scene['SoilMoi00_10cm_tavg']

pcm = sm.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap="RdYlBu",
    vmin=0, 
    vmax=0.5,
    cbar_kwargs={
        "label": "Soil Moisture (0-10 cm) [m³/m³]",
        "shrink": 0.8
    }
)

# --- Overlay dust points for this day
dust_on_peak_day = wldas_dust.where(
    wldas_dust.time == peak_dust_day,
    drop=True
)

ax.scatter(
    dust_on_peak_day.lon,
    dust_on_peak_day.lat,
    s=25,
    c="red",
    edgecolor="black",
    linewidth=0.5,
    transform=ccrs.PlateCarree(),
    label="Dust events"
)

# --- Map features
ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
ax.add_feature(cfeature.BORDERS, linewidth=0.6)
ax.add_feature(cfeature.STATES, linewidth=0.4)

ax.set_title(
    f"WLDAS Soil Moisture and Dust Events\n{peak_dust_day.strftime('%Y-%m-%d')}",
    fontsize=14
)

ax.legend(loc="lower left")

soil_orders._plot_save(fig, plot_dir="figures", plot_name="soil_moisture_example" )

