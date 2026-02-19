from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders

from pathlib import Path
import xarray as xr
import rioxarray as rxr
import pandas as pd
import os
from pyproj import CRS, Transformer
import rasterio
import numpy as np
import matplotlib.pyplot as plt

def main():
    # Paths for cached datasets
    processed_wldas_path = Path("data/processed/wldas_sample")
    wldas_path = "/mnt/data2/jturner/wldas_data"

    #--- Option to re-run the cached moisture datasets
    rerun_moisture_data = False

    print("Opening dust dataset...")
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name=location_name)
    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"],
        format="%Y%m%d"
    )

    if rerun_moisture_data:
        print("--- Rerunning WLDAS processing into xarray datasets ---")
        wldas_total = create_wldas_total(wldas_path, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        wldas_total = xr.open_dataset(processed_wldas_path / "wldas_total.nc")

    #--- This is out-of-date now that wldas_dust is not created
    # import figure_5a_moisture_bar as fig_5a
    # fig_5a.plot_bar_chart_moisture(wldas_total, wldas_dust)

    dust_df = add_surface_usage_to_dust_df(dust_df, location_name)
    dust_df = add_wldas_moisture_to_dust_df(wldas_total, dust_df)
    print(dust_df)
    
    plot_moisture_usage_cdf_heatmap(dust_df)

    return

#------------------------

def create_wldas_total(wldas_path, dust_df):
    print("Opening WLDAS files for each dust date...")
    
    wldas_files_every_dust = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['Date (YYYYMMDD)'].astype(str)
    ]

    existing_files = []
    missing_files = []

    for f in wldas_files_every_dust:
        if Path(f).exists():
            existing_files.append(f)
        else:
            missing_files.append(f)
    if missing_files:
        print(f"WARNING: {len(missing_files)} files from dust dataframe not found in WLDAS:")
        for f in missing_files:
            print(f"  - {f}")

    print(f"Opening {len(existing_files)}/{len(wldas_files_every_dust)} WLDAS files...")    
    wldas_total = xr.open_mfdataset(
        existing_files,
        combine="by_coords",
        drop_variables="time_bnds"
    )
    return wldas_total

def saving_processed_files(processed_wldas_path, wldas_total):
    print("Saving processed files as NetCDFs...")
    processed_wldas_path.parent.mkdir(parents=True, exist_ok=True)

    #--- Coarsen resolution for wldas_total
    COARSEN_LAT = 24
    COARSEN_LON = 24
    wldas_total = (
        wldas_total
        .coarsen(lat=COARSEN_LAT, lon=COARSEN_LON, boundary="trim")
        .mean()
    )

    wldas_total.to_netcdf(processed_wldas_path / "wldas_total_18.nc")
    print(f"Saved wldas_total → {processed_wldas_path}")

    return

def add_surface_usage_to_dust_df(dust_df, location_name):
    print("Opening surface usage dataset...")
    cec_filepath = (
        "data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif"
    )
    cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)
    src_crs = CRS.from_epsg(4326) 

    print("Cropping surface usage raster...")
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    dst_crs = CRS.from_wkt(cec_full.rio.crs.to_wkt()) 
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True) 
    minx, miny = transformer.transform(min_lon, min_lat) 
    maxx, maxy = transformer.transform(max_lon, max_lat) 
    minx, maxx = sorted([minx, maxx]) 
    miny, maxy = sorted([miny, maxy]) 
    cec_cropped = cec_full.rio.clip_box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    output_path = "data/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
    if not os.path.exists(output_path):
        print("Reprojecting to lat/lon...") 
        cec = cec_cropped.rio.reproject( 
            "EPSG:4326", 
            resolution=0.05, 
            resampling=rasterio.enums.Resampling.nearest)
        cec.rio.to_raster(output_path)
    else:
        print("Processed raster already exists — skipping reprojection.")
        cec = rxr.open_rasterio(output_path).squeeze("band", drop=True)

    print("Add usage values to dust dataframe...")
    dust_lats = xr.DataArray(dust_df["latitude"].values, dims="points")
    dust_lons = xr.DataArray(dust_df["longitude"].values, dims="points")

    usage_vals = cec.sel(
        x=dust_lons,
        y=dust_lats,
        method="nearest"
    ).values.squeeze().astype(int) 

    dust_df["usage"] = usage_vals
    return dust_df

def add_wldas_moisture_to_dust_df(wldas_total, dust_df):
    print("Adding WLDAS moisture to dust dataframe...")

    wldas_dates = pd.to_datetime(wldas_total.time.values).normalize()
    wldas_dates_set = set(wldas_dates.values)

    dust_df['moisture'] = None
    skipped_no_wldas_date = 0

    for idx, row in dust_df.iterrows():
        dust_time = row['datetime'].normalize()

        if dust_time.to_datetime64() not in wldas_dates_set:
            skipped_no_wldas_date += 1
            continue

        try:
            wldas_point = wldas_total.sel(
                time=dust_time,
                lat=row['latitude'],
                lon=row['longitude'],
                method="nearest"
            )['SoilMoi00_10cm_tavg'].values.item()

            dust_df.at[idx, 'moisture'] = wldas_point

        except KeyError as e:
            print(f"Skipping row {idx}: {e}")

    print(f"Total dust points: {len(dust_df)}")
    print(f"Skipped (no matching WLDAS date): {skipped_no_wldas_date}")
    print(f"Dust points tracked: {dust_df['moisture'].notna().sum()}")

    return dust_df

def plot_moisture_usage_cdf_heatmap(dust_df):
    print("Building and plotting the cumulative distribution function...")
    #freq of dust = blowing per domain / domain count 
    dust_df = dust_df.sort_values(['usage', 'moisture'])
    dust_df['cum_pct'] = dust_df.groupby('usage').cumcount() + 1
    dust_df['cum_pct'] = dust_df['cum_pct'] / dust_df.groupby('usage')['cum_pct'].transform('max') * 100

    moist_bins = np.linspace(0, 0.5, 11)

    dust_df.loc[dust_df['moisture'].notna(), 'moisture_bin'] = pd.cut(
        dust_df.loc[dust_df['moisture'].notna(), 'moisture'], 
        bins=moist_bins, 
        right=False
    )
    # dust_df['moist_bin'] = pd.cut(
    #     dust_df['moisture'],
    #     bins=moist_bins,
    #     right=False
    # )
    print(dust_df)

    heatmap_data = dust_df.pivot_table(
        index='usage',
        columns='moisture_bin',
        values='cum_pct',
        aggfunc='mean',
        fill_value=0, 
        observed=False  
    )

    land_cover_dict = {
        1: "Temp/Sub-polar Needleleaf Forest",
        2: "Sub-polar Taiga Needleleaf Forest",
        3: "Tropical Broadleaf Evergreen Forest",
        4: "Tropical Broadleaf Deciduous Forest",
        5: "Temp/Sub-polar Broadleaf Deciduous Forest",
        6: "Mixed Forest",
        7: "Tropical/Sub-tropical Shrubland",
        8: "Temp/Sub-polar Shrubland",
        9: "Tropical/Sub-tropical Grassland",
        10: "Temp/Sub-polar Grassland",
        11: "Sub-polar Shrub-Lichen-Moss",
        12: "Sub-polar Grass-Lichen-Moss",
        13: "Sub-polar Barren-Lichen-Moss",
        14: "Wetland",
        15: "Cropland",
        16: "Barren Lands",
        17: "Urban and Built-up",
        18: "Water",
        19: "Snow and Ice",
    }

    fig, ax = plt.subplots(figsize=(9, 4))

    im = ax.imshow(
        heatmap_data.values, 
        aspect='auto', 
        cmap='binary',
        origin='lower',
        vmax=100
    )

    ax.set_yticks(np.arange(heatmap_data.shape[0]))
    ax.set_yticklabels([land_cover_dict[u] for u in heatmap_data.index])

    ax.set_xlabel('Moisture (m3/m3)', size=15)
    ax.set_title('Dust events by surface moisture and \n land usage category', size=18)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label('Cumulative Percentage', size=15)
    cbar.ax.tick_params(labelsize=12)

    plt.tight_layout()
    plt.savefig(os.path.join("figures", "moisture_usage_cdf_heatmap.png"), bbox_inches='tight', dpi=300)
    plt.close(fig)

#------------------

if __name__ == "__main__":
    main()