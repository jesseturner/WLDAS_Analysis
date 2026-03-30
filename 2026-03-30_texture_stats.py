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

    dust_counts, dust_fraction, full_counts, full_fraction = calc_dust_counts_fraction(texture_ds, dust_df, texture_dict)
    print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction, texture_dict)
    return

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

#------------------------

if __name__ == "__main__":
    main()