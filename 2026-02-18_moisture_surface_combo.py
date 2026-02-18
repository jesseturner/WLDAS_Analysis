from modules_soil_moisture import utils_processing as wldas_proc
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
        saving_processed_files(processed_wldas_path, wldas_total, wldas_dust)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        wldas_total = xr.open_dataset(processed_wldas_path / "wldas_total.nc")

    # import figure_5a_moisture_bar as fig_5a
    # fig_5a.plot_bar_chart_moisture(wldas_total, wldas_dust)

    dust_df = add_surface_usage_to_dust_df(dust_df, location_name)
    dust_df = add_wldas_moisture_to_dust_df(wldas_total, dust_df)
    print(dust_df)
    
    return

#------------------------

def create_wldas_total(wldas_path, dust_df):
    print("Opening WLDAS files for each dust date...")
    
    wldas_files = [
        f"{wldas_path}/WLDAS_NOAHMP001_DA1_{d}.D10.nc.SUB.nc4"
        for d in dust_df['Date (YYYYMMDD)'].astype(str)
    ]

    num_wldas_files = 20
    print(f"Only opening first {num_wldas_files} WLDAS files...")
    wldas_total = wldas_proc.open_wldas_files_as_xarray_ds(wldas_files[:num_wldas_files])
    return wldas_total

def saving_processed_files(processed_wldas_path, wldas_total, wldas_dust):
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

    wldas_dust.to_netcdf(processed_wldas_path / "wldas_dust_18.nc")
    print(f"Saved wldas_dust → {processed_wldas_path}")

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
            )['SoilMoi00_10cm_tavg'].values

            dust_df.at[idx, 'moisture'] = wldas_point

        except KeyError as e:
            print(f"Skipping row {idx}: {e}")

    print(f"Total dust points: {len(dust_df)}")
    print(f"Skipped (no matching WLDAS date): {skipped_no_wldas_date}")
    print(f"Dust points tracked: {dust_df['moisture'].notna().sum()}")

    return dust_df



#------------------

if __name__ == "__main__":
    main()