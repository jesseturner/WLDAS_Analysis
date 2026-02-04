import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from modules_texture import gldas_texture_utils as gldas
from modules_line_dust import line_dust_utils as dust

#--- Open GLDAS soil textures
gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
location_name = "American Southwest"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
print(texture_ds)

#--- Make GLDAS soil textures figures
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name="American Southwest")

texture_categories = {
    1: "Sand",
    2: "Loamy Sand",
    3: "Sandy Loam",
    4: "Silt Loam",
    5: "Silt",
    6: "Loam",
    7: "Sandy Clay Loam",
    8: "Silty Clay Loam",
    9: "Clay Loam", 
    10: "Sandy Clay",
    11: "Silty Clay",
    12: "Clay", 
    13: "Organic Matter",
    14: "Water", 
    15: "Bedrock",
    16: "Other",
}

texture_colors = [
    "#f4e7b0",  # Sand
    "#e6d591",  # Loamy Sand
    "#d9c070",  # Sandy Loam
    "#c0b080",  # Silt Loam
    "#b0a070",  # Silt
    "#a67c52",  # Loam
    "#b77c4d",  # Sandy Clay Loam
    "#9c6644",  # Silty Clay Loam
    "#805533",  # Clay Loam
    "#8c3f2f",  # Sandy Clay
    "#6e2f23",  # Silty Clay
    "#4f1f18",  # Clay
    "#1a1a1a",  # Organic Matter
    "#3399ff",  # Water
    "#808080",  # Bedrock
    "#ffffff",  # Other
]

soil_cmap = ListedColormap(texture_colors, name="soil_textures")

cmap = plt.get_cmap("tab20")
cmap_colors = cmap(np.linspace(0, 1, len(texture_categories)))    

def _plot_gldas_soil_texture_map(texture_ds, dust_df, soil_cmap, texture_colors, location_name, texture_categories):
    from matplotlib.patches import Patch

    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()})

    texture_da = texture_ds.GLDAS_soiltex

    texture_da.plot(
        ax=ax,
        cmap=soil_cmap,
        add_colorbar=False,
        transform=ccrs.PlateCarree()
    )

    #--- Plot dust points
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
    min_lat, max_lat, min_lon, max_lon = gldas._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    
    ax.set_title("Soil Textures with Dust Origins")
    legend_handles = [
        Patch(facecolor=color, edgecolor="black", label=label)
        for label, color in zip(texture_categories.values(), texture_colors)
    ]

    dust_handle = Patch(
        facecolor="white",
        edgecolor="black",
        label="Dust Origin"
    )
    ax.legend(
        handles=legend_handles + [dust_handle],
        title="Soil Texture",
        loc="lower left",
        frameon=True
    )

    gldas._plot_save(fig, fig_dir="figures", fig_name="gldas_texture_categories")
    
    return

def _plot_gldas_soil_texture_bar(texture_ds, dust_df, texture_colors, texture_categories, location_name):
    """
    Create a side-by-side bar chart comparing:
    - frequency of soil textures at dust points
    - frequency of soil textures in the full soil raster
    """
    from matplotlib.patches import Patch

    # Extract the soil texture DataArray
    texture_da = texture_ds.GLDAS_soiltex

    # Flatten the raster to 1D for counting
    texture_flat = texture_da.values.flatten()

    # Count full domain occurrences
    full_counts = {k: np.sum(texture_flat == k) for k in texture_categories.keys()}
    total_full = sum(full_counts.values())
    full_fraction = {k: v / total_full for k, v in full_counts.items()}

    # Subset raster at dust point locations
    # Round coordinates to nearest grid point
    dust_textures = []
    for lon, lat in zip(dust_df["longitude"], dust_df["latitude"]):
        # Select nearest pixel
        val = texture_da.sel(
            lon=lon, lat=lat, method="nearest"
        ).values
        dust_textures.append(val)

    dust_counts = {k: dust_textures.count(k) for k in texture_categories.keys()}
    total_dust = sum(dust_counts.values())
    dust_fraction = {k: v / total_dust for k, v in dust_counts.items()}

    # Prepare for plotting
    categories = list(texture_categories.keys())
    labels = [texture_categories[k] for k in categories]
    x = np.arange(len(categories))
    width = 0.4

    fig, ax = plt.subplots(figsize=(16, 8))

    # Plot bars
    for i, k in enumerate(categories):
        color = texture_colors[i]
        ax.bar(x[i] - width / 2, dust_fraction[k], width, color=color, edgecolor="black", label="Dust points" if i == 0 else "")
        ax.bar(x[i] + width / 2, full_fraction[k], width, color=color, alpha=0.5, label="Full domain" if i == 0 else "")

    # Labels and ticks
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Fraction of observations")
    ax.set_xlabel("Soil Texture")
    ax.set_title(f"Soil Texture Frequency in {location_name}: Dust Points vs Full Domain")

    # Legend
    legend_elements = [
        Patch(facecolor="gray", edgecolor="black", label="Dust points"),
        Patch(facecolor="gray", edgecolor="black", alpha=0.5, label="Full domain")
    ]
    ax.legend(handles=legend_elements, title="Dataset")

    gldas._plot_save(fig, fig_dir="figures", fig_name="gldas_texture_categories_bar")

    return

_plot_gldas_soil_texture_map(texture_ds, dust_df, soil_cmap, texture_colors, location_name, texture_categories)
_plot_gldas_soil_texture_bar(texture_ds, dust_df, texture_colors, texture_categories, location_name)