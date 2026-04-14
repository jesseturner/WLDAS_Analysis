from pathlib import Path
import pandas as pd
import xarray as xr
import sys
import os
import rioxarray as rxr
import numpy as np

from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders
from modules_texture import gldas_texture_utils as gldas

def main():
    print("Getting dust data...")
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name) 
    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"],
        format="%Y%m%d"
    )

    #--- Paths for cached datasets
    processed_wldas_path = Path("data/processed/wldas_sample/wldas_total_2026_02_18.nc")
    processed_wind_path = Path("/mnt/data2/jturner/narr/processed/narr_daytime_wnd_max.nc")

    wldas_path = "/mnt/data2/jturner/wldas_data"

    #--- Option to re-run the cached moisture datasets
    rerun_moisture_data = False

    if rerun_moisture_data:
        print("--- Rerunning WLDAS processing into xarray datasets ---")
        wldas_total = create_wldas_total(wldas_path, dust_df)
        saving_processed_files(processed_wldas_path, wldas_total)
        
    else:
        print(f"Loading cached wldas data from {processed_wldas_path}")
        wldas_total = xr.open_dataset(processed_wldas_path)

    dust_df = add_static_data(dust_df, location_name)
    dust_df = add_wldas_moisture_to_dust_df(wldas_total, dust_df)
    dust_df = add_winds_to_dust_df(processed_wind_path, dust_df)
    dust_df_sorted_wind, column_name, selected_list, colors, save_name = soil_order_info_for_cdf(dust_df, sort_by="wind_speed")
    dust_df_sorted_moisture, column_name, selected_list, colors, save_name = soil_order_info_for_cdf(dust_df, sort_by="moisture")

    print_cdf_stats(dust_df_sorted_moisture, dust_df_sorted_wind)

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

    wldas_total.to_netcdf(processed_wldas_path)
    print(f"Saved wldas_total → {processed_wldas_path}")

    return

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

def add_winds_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")

    def nearest_grid_point(lat2d, lon2d, lat, lon):
        dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
        iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
        return iy, ix
    lat2d = ds_ws["lat"].values
    lon2d = ds_ws["lon"].values

    dust_winds = []
    for _, row in dust_df.iterrows():
        iy, ix = nearest_grid_point(lat2d, lon2d, row["latitude"], row["longitude"])
        
        #--- Day-of time match 
        ws = ds_ws["wind_speed"].sel(
            time=row["datetime"].floor("D"),
            method="nearest"
        ).isel(y=iy, x=ix)
        
        dust_winds.append(ws.compute().item())

    dust_winds = np.array(dust_winds)
    dust_df["wind_speed"] = dust_winds
    dust_df = dust_df.dropna(subset=["wind_speed"])

    return dust_df

def soil_order_info_for_cdf(dust_df, sort_by):

    if sort_by not in {"moisture", "wind_speed"}:
        raise ValueError("sort_by can only handle moisture and wind_speed")
    
    print("Getting soil order names and choosing which to plot...")
    order_dict = orders.get_soil_order_dict()
    dust_df["soil_order_name"] = dust_df["soil_order"].map(order_dict)
    selected_soil_orders = ['Aridisols', 'Entisols', 'Mollisols', 'Alfisols', 'Shifting Sands']
    dust_df_filtered = dust_df[dust_df["soil_order_name"].isin(selected_soil_orders)]

    colors = [
        "#f1af4c", #Aridisols
        "#dc5908", #Entisols
        "#046a2b", #Mollisols
        "#06dd0a", #Alfisols
        "#a8a6a4" #Shifting Sands
    ]
    save_name = "moisture_order_cdf.png"
    column_name = "soil_order_name"
    
    print("Building and plotting the order cumulative distribution function...")
    if sort_by == "moisture":
        dust_df_sorted = dust_df_filtered.sort_values(['soil_order_name', sort_by], ascending=False)
    if sort_by == "wind_speed":
        dust_df_sorted = dust_df_filtered.sort_values(['soil_order_name', sort_by], ascending=True)

    dust_df_sorted['cum_pct'] = dust_df_sorted.groupby('soil_order_name').cumcount() + 1
    dust_df_sorted['cum_pct'] = dust_df_sorted['cum_pct'] / dust_df_sorted.groupby('soil_order_name')['cum_pct'].transform('max') * 100

    return dust_df_sorted, column_name, selected_soil_orders, colors, save_name

def print_cdf_stats(dust_df_sorted_moisture, dust_df_sorted_wind):

    #--- Get specific thresholds from the CDF
    idx = (dust_df_sorted_moisture['moisture'] - 0.15).abs().groupby(dust_df_sorted_moisture['soil_order_name']).idxmin()
    result = dust_df_sorted_moisture.loc[idx, ['soil_order_name', 'cum_pct']]
    print(result)
    idx = (dust_df_sorted_wind['wind_speed'] - 10).abs().groupby(dust_df_sorted_wind['soil_order_name']).idxmin()
    result = dust_df_sorted_wind.loc[idx, ['soil_order_name', 'cum_pct']]
    print(result)

    #--- Get average moisture and wind speed by category
    result = dust_df_sorted_moisture.groupby('soil_order_name')['moisture'].mean()
    print("Moisture means \n", result)
    result = dust_df_sorted_wind.groupby('soil_order_name')['wind_speed'].mean()
    print("Wind speed means \n", result)

    #--- Get the most common category associations
    counts = (
        dust_df_sorted_moisture.groupby('soil_order_name')['texture']
        .value_counts()
        .rename('count')
        .reset_index()
    )
    totals = counts.groupby('soil_order_name')['count'].transform('sum')
    counts['percent'] = counts['count'] / totals
    result = counts.loc[counts.groupby('soil_order_name')['count'].idxmax()]
    print("Most common texture for each soil order: \n", result)

    counts = (
        dust_df_sorted_moisture.groupby('soil_order_name')['usage']
        .value_counts()
        .rename('count')
        .reset_index()
    )
    totals = counts.groupby('soil_order_name')['count'].transform('sum')
    counts['percent'] = counts['count'] / totals
    result = counts.loc[counts.groupby('soil_order_name')['count'].idxmax()]
    print("Most common usage for each soil order: \n", result)

    return 


#------------------------

if __name__ == "__main__":
    main()