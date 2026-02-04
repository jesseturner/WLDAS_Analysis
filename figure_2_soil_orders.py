import rioxarray as rxr
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

from modules_soil_orders import soil_orders_utils as orders
from modules_line_dust import line_dust_utils as dust


usda_filepath = "data/raw/soil_types_usda/suborder2006.tif"
location_name="American Southwest"

dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

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

#--- Get colormap associated with soil order names
#------ Colormaps not synced up due to spatial plot not following
soil_order_dict = orders._get_soil_order_dict() 

category_colors = {
    "Alfisols": "#06dd0a",
    "Andisols": "#f603d6", 
    "Aridisols": "#f1af4c",
    "Entisols": "#dc5908", 
    "Gelisols": "#730ef8",
    "Histosols": "#61310d", 
    "Inceptisols": "#cada9c",
    "Mollisols": "#046a2b",
    "Oxisols": "#ff0e0e", 
    "Spodosols": "#f084e0", 
    "Ultisols": "#f9ec3a",
    "Vertisols": "#1411f5",
    "Rocky Land": "#6b6969", 
    "Salt flats": "#e0e0e0", 
    "Shifting Sands": "#a8a6a4",
    "Water": "#a3d2f3", 
    "Ice/Glacier": "#aec7e8", 
    "No data": "#ffffff", 
    "Urban, mining": "#7f7f7f", 
    "Human disturbed": "#000000",
    "Fishpond": "#1f77b4", 
    "Island": "#aec7e8",    
}

unique_orders = list(dict.fromkeys(soil_order_dict.values()))
order_to_index = {order: i for i, order in enumerate(unique_orders)}
colors = [category_colors[o] for o in unique_orders]
cmap = mcolors.ListedColormap(colors)
n_categories = len(unique_orders)
norm = mcolors.BoundaryNorm(boundaries=np.arange(-0.5, n_categories+0.5, 1), ncolors=n_categories)

default_order = "No data"
flat_values = soil_da.values.ravel()
flat_indices = np.array([
    order_to_index.get(soil_order_dict.get(int(code), default_order), order_to_index[default_order])
    for code in flat_values
])
soil_indices = soil_da.copy()
soil_indices.values = flat_indices.reshape(soil_da.shape)


def _plot_usda_soil_types_map(soil_indices, dust_df, location_name, unique_orders, cmap, norm, colors):

    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()})

    soil_indices.plot(
        ax=ax,
        cmap=cmap,
        norm=norm,
        add_colorbar=False,
        transform=ccrs.PlateCarree()
    )

    # Plot dust points
    ax.scatter(
        dust_df["longitude"],
        dust_df["latitude"],
        transform=ccrs.PlateCarree(),
        s=12,
        marker="o",
        facecolors='white',
        edgecolors='black',
        linewidth=1, 
        alpha=0.5,
        zorder=2
    )

    ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    
    ax.set_title("USDA Soil Orders with Dust Origins")

    unique_indices = np.unique(soil_indices.values)
    legend_elements = [
        Patch(facecolor=colors[i], label=name)
        for i, name in enumerate(unique_orders)
        if i in unique_indices
    ]
    ax.legend(
        handles=legend_elements,
        title="Soil Order",
        bbox_to_anchor=(1.05, 1),
        loc="upper left"
    )

    orders._plot_save(fig, plot_dir="figures", plot_name="usda_soil_types")
    return

def _plot_usda_soil_types_bar(soil_da, dust_df, order_to_index, cmap):
    """
    Create a side-by-side bar chart comparing:
    - frequency of soil orders at dust points
    - frequency of soil orders in the full soil raster
    """

    lons = soil_da["x"].values
    lats = soil_da["y"].values
    soil_values = soil_da.values

    soil_order_dict = orders._get_soil_order_dict()

    dust_lons = dust_df["longitude"].values
    dust_lats = dust_df["latitude"].values

    x_idx = np.abs(lons[None, :] - dust_lons[:, None]).argmin(axis=1)
    y_idx = np.abs(lats[None, :] - dust_lats[:, None]).argmin(axis=1)

    soil_codes_at_points = soil_values[y_idx, x_idx]

    soil_orders_at_points = []
    for code in soil_codes_at_points:
        if np.isnan(code):
            continue
        code = int(code)
        if code not in soil_order_dict:
            print(f"Unknown soil code: {code}")
            soil_orders_at_points.append("Unknown")
        else:
            soil_orders_at_points.append(soil_order_dict[code])

    point_counts = pd.Series(soil_orders_at_points).value_counts()

    flat_codes = soil_values.flatten()
    flat_codes = flat_codes[~np.isnan(flat_codes)]

    soil_orders_full = [soil_order_dict.get(int(code), "Unknown") for code in flat_codes]
    full_counts = pd.Series(soil_orders_full).value_counts()

    counts_df = pd.DataFrame({
        "Dust points": point_counts,
        "Full domain": full_counts
    }).fillna(0)

    print(point_counts)
    counts_df = counts_df.drop(index="Unknown", errors="ignore")
    counts_df = counts_df.drop(index="No data", errors="ignore")
    counts_df = counts_df.div(counts_df.sum())
    counts_df = counts_df.sort_values("Dust points", ascending=False)

    fig, ax = plt.subplots(figsize=(11, 6))

    x = np.arange(len(counts_df))
    width = 0.35

    for i, soil_order in enumerate(counts_df.index):
        idx = order_to_index.get(soil_order, order_to_index["No data"])
        
        color = cmap(idx)

        ax.bar(
            x[i] - width / 2,
            counts_df.loc[soil_order, "Dust points"],
            width,
            color=color,
            edgecolor="black",
            linewidth=1
        )

        ax.bar(
            x[i] + width / 2,
            counts_df.loc[soil_order, "Full domain"],
            width,
            color=color,
            alpha=0.5
        )

    ax.set_xticks(x)
    ax.set_xticklabels(counts_df.index, rotation=45, ha="right")
    ax.set_ylabel("Fraction of observations")
    ax.set_xlabel("Soil Order")
    ax.set_title("Soil Order Frequency: Dust Points vs Full Domain")

    legend_elements = [
        Patch(facecolor="black", label="Dust points"),
        Patch(facecolor="black", alpha=0.5, label="Full domain")
    ]
    ax.legend(handles=legend_elements, title="Dataset")

    plt.tight_layout()
    orders._plot_save(fig, plot_dir="figures", plot_name="usda_soil_types_bar")

    return


_plot_usda_soil_types_map(soil_indices, dust_df, location_name, unique_orders, cmap, norm, colors)
_plot_usda_soil_types_bar(soil_da, dust_df, order_to_index, cmap)