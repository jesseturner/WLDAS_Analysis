import rioxarray as rxr
import xarray as xr
import os
import numpy as np
from scipy.stats import norm

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders
from modules_texture import gldas_texture_utils as gldas


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

    print("Proportion tests...") 

    print("CDF tests...")
    #--- get these from 2026-03-31
    dust_df = add_static_data(dust_df, location_name)


    return

#------------------------

def calc_dust_counts_fraction(texture_da, dust_df, texture_dict):

    # Flatten the raster to 1D for counting
    texture_flat = texture_da.values.flatten()

    # Count full domain occurrences
    full_counts = {k: np.sum(texture_flat == k) for k in texture_dict.keys()}
    from collections import Counter
    mapped_full = [texture_dict.get(val) for val in texture_flat if val in texture_dict]
    full_counts = Counter(mapped_full)
    total_full = sum(full_counts.values())
    full_fraction = {k: v / total_full for k, v in full_counts.items()}

    # Subset raster at dust point locations
    # Round coordinates to nearest grid point
    dust_textures = []
    for lon, lat in zip(dust_df["longitude"], dust_df["latitude"]):
        # Select nearest pixel
        val = texture_da.sel(
            x=lon, y=lat, method="nearest"
        ).values.item()
        dust_textures.append(val)

    # dust_counts = {k: dust_textures.count(k) for k in texture_dict.keys()}
    # Map dust values → category
    mapped_dust = [texture_dict.get(val) for val in dust_textures if val in texture_dict]
    dust_counts = Counter(mapped_dust)
    total_dust = sum(dust_counts.values())
    dust_fraction = {k: v / total_dust for k, v in dust_counts.items()}

    return dust_counts, dust_fraction, full_counts, full_fraction

def print_ttest_results(dust_counts, dust_fraction, full_counts, full_fraction):
    print("\n===== Soil Texture Significance Tests =====")
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

def add_static_data(dust_df, location_name):
    #--- USAGE DATA
    cover_data_path = "data/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
    if os.path.exists(cover_data_path):
        print("Opening surface usage dataset...")
        usage = rxr.open_rasterio(cover_data_path).squeeze("band", drop=True)
    else:
        print("Land cover data not found, exiting...")
        
    print("For each dust event, getting the usage...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

    usage_vals = usage.sel(
        x=dust_lons,
        y=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 

    dust_df["usage"] = usage_vals

    #--- TEXTURE DATA
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

    #--- SOIL ORDERS DATA
    print("Opening soil orders dataset...")
    usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
    location_name="American Southwest"
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

    print("Add soil order values to dust dataframe...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")
    soil_vals = soil_da.sel(
        x=dust_lons,
        y=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 
    dust_df["soil_order"] = soil_vals

    return dust_df

#------------------------

if __name__ == "__main__":
    main()