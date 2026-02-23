import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from scipy.stats import norm
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from modules_texture import gldas_texture_utils as gldas
from modules_line_dust import line_dust_utils as dust

def main():
    #--- Open GLDAS soil textures
    gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
    location_name = "American Southwest"
    texture_ds = gldas.open_gldas_file(gldas_path)
    texture_ds = gldas.filter_to_region(texture_ds, location_name)

    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name="American Southwest")

    texture_dict = gldas.get_texture_dict()

    texture_colors = [
        "#ff0000",  # Sand
        "#e6d591",  # Loamy Sand
        "#d9c070",  # Sandy Loam
        "#c0b080",  # Silt Loam
        "#b0a070",  # Silt
        "#a67c52",  # Loam
        "#00ffb7",  # Sandy Clay Loam
        "#9c6644",  # Silty Clay Loam
        "#805533",  # Clay Loam
        "#8c3f2f",  # Sandy Clay
        "#fd009c",  # Silty Clay
        "#4f1f18",  # Clay
        "#1a1a1a",  # Organic Matter
        "#3399ff",  # Water
        "#808080",  # Bedrock
        "#ffffff",  # Other
    ]
    soil_cmap = ListedColormap(texture_colors, name="soil_textures")

    dust_counts, dust_fraction, full_counts, full_fraction = calc_dust_counts_fraction(texture_ds, dust_df, texture_dict)
    print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction, texture_dict)
    plot_gldas_soil_texture_bar(dust_fraction, full_fraction, texture_colors, texture_dict, location_name)
    plot_gldas_soil_texture_map(texture_ds, dust_df, soil_cmap, texture_colors, location_name, texture_dict)
    return

#------------------------

def calc_dust_counts_fraction(texture_ds, dust_df, texture_dict):

    # Extract the soil texture DataArray
    texture_da = texture_ds.GLDAS_soiltex

    # Flatten the raster to 1D for counting
    texture_flat = texture_da.values.flatten()

    # Count full domain occurrences
    full_counts = {k: np.sum(texture_flat == k) for k in texture_dict.keys()}
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

    dust_counts = {k: dust_textures.count(k) for k in texture_dict.keys()}
    total_dust = sum(dust_counts.values())
    dust_fraction = {k: v / total_dust for k, v in dust_counts.items()}

    return dust_counts, dust_fraction, full_counts, full_fraction

def print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction, texture_dict):
    print("\n===== Soil Texture Significance Tests =====")
    total_dust = sum(dust_counts.values())
    total_full = sum(full_counts.values())

    for k in texture_dict.keys():
        t_stat, p_val = proportion_ttest(
            dust_counts[k], total_dust,
            full_counts[k], total_full
        )

        significance = ""
        if p_val < 0.001:
            significance = "***"
        elif p_val < 0.01:
            significance = "**"
        elif p_val < 0.05:
            significance = "*"

        print(
            f"{texture_dict[k]:20s} | "
            f"dust={dust_fraction[k]:.3f} "
            f"full={full_fraction[k]:.3f} | "
            f"t={t_stat:7.3f}  p={p_val:.3e} {significance}"
        )
    return

def plot_gldas_soil_texture_bar(dust_fraction, full_fraction, texture_colors, texture_dict, location_name):
    """
    Create a side-by-side bar chart comparing:
    - frequency of soil textures at dust points
    - frequency of soil textures in the full soil raster
    """

    # Prepare for plotting
    categories = list(texture_dict.keys())
    labels = [texture_dict[k] for k in categories]
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

def proportion_ttest(x1, n1, x2, n2):
    """
    Two-sample test for difference in proportions.
    Returns (t_stat, p_value).
    """

    if n1 == 0 or n2 == 0:
        return np.nan, np.nan

    p1 = x1 / n1
    p2 = x2 / n2

    # pooled proportion
    p_pool = (x1 + x2) / (n1 + n2)

    # standard error
    se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))

    if se == 0:
        return np.nan, np.nan

    t_stat = (p1 - p2) / se

    # two-sided p-value
    p_value = 2 * (1 - norm.cdf(abs(t_stat)))

    return t_stat, p_value

def plot_gldas_soil_texture_map(texture_ds, dust_df, soil_cmap, texture_colors, location_name, texture_dict):
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
        for label, color in zip(texture_dict.values(), texture_colors)
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

#------------------------

if __name__ == "__main__":
    main()