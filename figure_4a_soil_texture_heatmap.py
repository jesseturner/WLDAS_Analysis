import rioxarray as rxr
import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import os

from modules_line_dust import line_dust_utils as dust
from modules_texture import gldas_texture_utils as gldas
from modules_soil_orders import soil_orders_utils as orders

location_name = "American Southwest"

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)

#--- Get soil texture data
gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
texture_da = texture_ds.GLDAS_soiltex

#--- Get soil order data
usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
soil_da = (
    rxr.open_rasterio(usda_filepath)
    .squeeze("band", drop=True)
    .rio.clip_box(
        minx=min_lon,
        miny=min_lat,
        maxx=max_lon,
        maxy=max_lat,
    )
)

#--- Ensure consistent coordinate names
texture = texture_da.rename({"lat": "y", "lon": "x"})
soil = soil_da.rename({"y": "y", "x": "x"})

#--- Create DataArrays of dust coordinates
dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

#--- Sample nearest grid cell
texture_vals = texture.sel(
    x=dust_lons,
    y=dust_lats,
    method="nearest"
).values.squeeze().astype(int) 

soil_vals = soil.sel(
    x=dust_lons,
    y=dust_lats,
    method="nearest"
).values

#--- Attach to DataFrame
dust_df["texture"] = texture_vals
dust_df["soil"] = soil_vals

#--- Count combinations
combo_counts = (
    dust_df
    .groupby(["soil", "texture"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

#--- Count combinations total
texture2d = texture_da.isel(time=0)
texture_df = texture2d.to_dataframe(name="texture").reset_index()
texture_df["texture"] = texture_df["texture"].fillna(0).astype(int)

soil_at_texture = soil_da.sel(
    x=xr.DataArray(texture_df["lon"].values, dims="points"),
    y=xr.DataArray(texture_df["lat"].values, dims="points"),
    method="nearest"
).values

texture_df["soil"] = soil_at_texture
texture_df = texture_df[texture_df["soil"] != soil_da._FillValue]

combo_counts_total = (
    texture_df
    .groupby(["soil", "texture"])
    .size()
    .reset_index(name="count")
    .sort_values("count", ascending=False)
)

#--- Map to category names
soil_order_dict = orders.get_soil_order_dict() 
texture_dict = gldas.get_texture_dict()

combo_counts["texture_name"] = combo_counts["texture"].map(texture_dict)
combo_counts["soil_name"] = combo_counts["soil"].map(soil_order_dict)
combo_counts_total["texture_name"] = combo_counts_total["texture"].map(texture_dict)
combo_counts_total["soil_name"] = combo_counts_total["soil"].map(soil_order_dict)

#--- Plot heatmap
def plot_soil_texture_matrix(df, ax, textures, soils, title):
    matrix = df.pivot_table(
        index="soil_name",
        columns="texture_name",
        values="count",
        aggfunc="sum",
        fill_value=0
    )

    matrix = matrix.reindex(
        index=soils,
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
soils_ref = sorted(combo_counts["soil_name"].dropna().unique())
im1 = plot_soil_texture_matrix(combo_counts, axes[0], textures_ref, soils_ref, "Dust events")
im2 = plot_soil_texture_matrix(combo_counts_total, axes[1], textures_ref, soils_ref, "Full domain")


plt.savefig(os.path.join("figures", "soil_texture_heatmap"), bbox_inches='tight', dpi=300)
