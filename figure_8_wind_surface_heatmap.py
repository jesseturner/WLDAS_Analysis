from modules_line_dust import line_dust_utils as dust
from modules_texture import gldas_texture_utils as gldas

import xarray as xr
import numpy as np
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import os

print("Opening dust dataset...")
location_name = "American Southwest"
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)


print("Opening soil texture dataset...")
gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
texture_da = texture_ds.GLDAS_soiltex

print("Add texture values to dust dataframe...")
dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")
texture_vals = texture_da.sel(
    lon=dust_lons,
    lat=dust_lats,
    method="nearest"
).values.squeeze().astype(int) 
dust_df["texture"] = texture_vals

print("Opening data from NARR...")
cache_path = Path("/mnt/data2/jturner/narr/processed/narr_wind_speed.nc")
if cache_path.exists():
    print("Loading cached wind speed...")
    ds_ws = xr.open_dataset(cache_path)
else:
    print("Computing wind speed and saving to cache...")
    ds_uwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/uwnd.10m.20*.nc")
    ds_vwnd = xr.open_mfdataset("/mnt/data2/jturner/narr/vwnd.10m.20*.nc")

    ds = xr.merge([ds_uwnd, ds_vwnd])
    ds_ws = xr.Dataset(
        {"wind_speed": np.sqrt(ds["uwnd"]**2 + ds["vwnd"]**2)},
        coords=ds.coords,
        attrs=ds.attrs)
    ds_ws.to_netcdf(cache_path)

print("Temporarily filtering dust events to 2001-2003...")
dust_df["datetime"] = pd.to_datetime(
    dust_df["Date (YYYYMMDD)"],
    format="%Y%m%d"
)
dust_df = dust_df[
    dust_df["datetime"].dt.year.isin([2001, 2002, 2003])
].copy()

print("Spatial matching of wind grid...")
def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

lat2d = ds_ws["lat"].values
lon2d = ds_ws["lon"].values

print("Extracting wind speeds at dust events...")
dust_winds = []

for _, row in dust_df.iterrows():
    iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
    
    #--- Nearest-time match
    # ws = ds_ws["wind_speed"].sel(
    #     time=row["datetime"],
    #     method="nearest"
    # ).isel(y=iy, x=ix)
    
    #--- Day-of time match 
    ws = ds_ws["wind_speed"].sel(
        time=row["datetime"].floor("D"),
        method="nearest"
    ).isel(y=iy, x=ix)
    
    dust_winds.append(ws.compute().item())

dust_df["wind_speed"] = dust_winds
dust_df = dust_df.dropna(subset=["wind_speed"])

print("Binning wind speeds...")
wind_bins = [0, 3, 6, 9, 12, 15, 18, np.inf]
wind_labels = [
    "0-3",
    "3-6",
    "6-9",
    "9-12",
    "12-15",
    "15-18",
    "18+"
]
dust_df["wind_bin"] = pd.cut(
    dust_df["wind_speed"],
    bins=wind_bins,
    labels=wind_labels,
    right=False
)

print("Create dust grouping for heat map...")
combo_counts = (
    dust_df
    .groupby(["wind_bin", "texture"], observed=False)
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
texture_dict = gldas.get_texture_dict()
combo_counts["texture_name"] = combo_counts["texture"].map(texture_dict)
combo_counts["wind_bin"] = combo_counts["wind_bin"].astype(str)

print("Create total grouping for heat map...")
texture2d = texture_da.isel(time=0)
texture_df = texture2d.to_dataframe(name="texture").reset_index()
texture_df["texture"] = texture_df["texture"].fillna(0).astype(int)

texture_winds = []
for _, row in texture_df.iterrows():
    iy, ix = nearest_grid_point(lat2d, lon2d, row["lat"], row["lon"])
    
    #--- Day-of time match 
    ws = ds_ws["wind_speed"].sel(
        time=row["time"].floor("D"),
        method="nearest"
    ).isel(y=iy, x=ix)
    
    texture_winds.append(ws.compute().item())

texture_df["wind_speed"] = texture_winds
texture_df["wind_bin"] = pd.cut(
    dust_df["wind_speed"],
    bins=wind_bins,
    labels=wind_labels,
    right=False
)

combo_counts_total = (
    texture_df
    .groupby(["wind_bin", "texture"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)
combo_counts_total["texture_name"] = combo_counts_total["texture"].map(texture_dict)
combo_counts_total["wind_bin"] = combo_counts_total["wind_bin"].astype(str)

print("Plotting heat map...")
def plot_wind_texture_matrix(df, ax, textures, winds, title):
    matrix = df.pivot_table(
        index="wind_bin",
        columns="texture_name",
        values="count",
        aggfunc="sum",
        fill_value=0
    )

    matrix = matrix.reindex(
        index=winds,
        columns=textures,
        fill_value=0
    )

    total = matrix.values.sum()
    matrix = matrix / total

    vmax = np.max(matrix.values)

    im = ax.imshow(
        matrix.values,
        vmin=0,
        vmax=vmax,
        cmap="binary"
    )

    ax.set_xticks(np.arange(matrix.shape[1]))
    ax.set_yticks(np.arange(matrix.shape[0]))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right", size=12)
    ax.set_yticklabels(matrix.index, size=15)

    ax.set_title(title, size=18)

    # Cell labels (formatted as fraction or %)
    norm = im.norm
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            val = matrix.values[i, j]
            if val > 0:
                text_color = "white" if norm(val) > 0.5 else "black"

                ax.text(
                    j, i, f"{(val*100):.2f}",   # percent formatting
                    ha="center",
                    va="center",
                    fontsize=9,
                    color=text_color
                )

    return im

fig, axes = plt.subplots(
    nrows=1,
    ncols=2,
    figsize=(15, 6),
    sharey=True,
    constrained_layout=True)

textures_ref = sorted(combo_counts["texture_name"].dropna().unique())
textures_ref = [t for t in textures_ref if t != 'Other'] + ['Other'] # move 'Other' to end
winds_ref = [w for w in wind_labels
             if w in combo_counts["wind_bin"].values]
im1 = plot_wind_texture_matrix(combo_counts, axes[0], textures_ref, winds_ref, "Dust events")
im2 = plot_wind_texture_matrix(combo_counts_total, axes[1], textures_ref, winds_ref, "Full domain")

plt.savefig(os.path.join("figures", "winds_texture_heatmap"), bbox_inches='tight', dpi=300)