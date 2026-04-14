import rioxarray as rxr
import numpy as np
from scipy.stats import norm

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders


def main():
    print("Getting dust data...")
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name) 

    print("Getting soil order data...")
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

    soil_order_dict = orders.get_soil_order_dict()
    dust_counts, dust_fraction, full_counts, full_fraction = calc_dust_counts_fraction(soil_da, dust_df, soil_order_dict)
    print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction)

    return

#------------------------

def calc_dust_counts_fraction(soil_order_da, dust_df, soil_order_dict):

    # Flatten the raster to 1D for counting
    soil_order_flat = soil_order_da.values.flatten()

    # Count full domain occurrences
    full_counts = {k: np.sum(soil_order_flat == k) for k in soil_order_dict.keys()}
    from collections import Counter
    mapped_full = [soil_order_dict.get(val) for val in soil_order_flat if val in soil_order_dict]
    full_counts = Counter(mapped_full)
    total_full = sum(full_counts.values())
    full_fraction = {k: v / total_full for k, v in full_counts.items()}

    # Subset raster at dust point locations
    # Round coordinates to nearest grid point
    dust_soil_orders = []
    for lon, lat in zip(dust_df["longitude"], dust_df["latitude"]):
        # Select nearest pixel
        val = soil_order_da.sel(
            x=lon, y=lat, method="nearest"
        ).values.item()
        dust_soil_orders.append(val)

    # dust_counts = {k: dust_soil_orders.count(k) for k in soil_order_dict.keys()}
    # Map dust values → category
    mapped_dust = [soil_order_dict.get(val) for val in dust_soil_orders if val in soil_order_dict]
    dust_counts = Counter(mapped_dust)
    total_dust = sum(dust_counts.values())
    dust_fraction = {k: v / total_dust for k, v in dust_counts.items()}

    return dust_counts, dust_fraction, full_counts, full_fraction

def print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction):
    print("\n===== Soil Order Significance Tests =====")
    total_dust = sum(dust_counts.values())
    total_full = sum(full_counts.values())

    for k in dust_counts.keys():
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
            f"{k:20s} | "
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