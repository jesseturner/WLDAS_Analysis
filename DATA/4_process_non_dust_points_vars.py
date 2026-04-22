#--- Non-blowing dust origin points dataframe 
#--- with winds, moisture, static data

from pathlib import Path
import pandas as pd
import numpy as np
import xarray as xr
import sys, os
import rioxarray as rxr
from datetime import datetime

def main():
    #--- get dust data
    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = get_dust_df(dust_path)

    #--- create non-blowing dataframe
    non_dust_df = create_non_dust_df(dust_df)

    #--- wind data
    processed_wind_path = Path("DATA/processed/2_wind_grid_2026-04-22.nc")
    non_dust_df = add_winds_to_dust_df(processed_wind_path, non_dust_df)

    #--- moisture data
    #------ ADD filter to non-dust days
    processed_moisture_path = Path("DATA/processed/1_moisture_grid_2026-04-22.nc")
    non_dust_df = add_moisture_to_dust_df(processed_moisture_path, non_dust_df)

    #--- category data
    non_dust_df = add_static_data(non_dust_df, location_name)

    #--- save dataset
    timestamp = datetime.today().strftime("%Y-%m-%d")
    non_dust_df.to_csv(f"DATA/processed/4_non_dust_points_vars_{timestamp}.csv", index=False)

    return

#------------------------

def read_dust_data_into_df(dust_path):
    
    dust_df = pd.read_csv(dust_path, sep=r'\s+', skiprows=2, header=None)
    dust_df.columns = ['Date (YYYYMMDD)', 'start time (UTC)', 'latitude', 'longitude', 'Jesse check']

    #--- Clean lat/lon data
    dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
    dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')
    dust_df = dust_df.dropna(subset=['latitude', 'longitude'])

    return dust_df

def get_dust_df(dust_path):
    print("Opening dust data, creating dust dataframe... ")
    dust_df = read_dust_data_into_df(dust_path)

    dust_df["time_str"] = (
        dust_df["start time (UTC)"]
        .astype("Int64")        # allows NaNs safely
        .astype(str)
        .str.zfill(4)
    )

    dust_df["datetime"] = pd.to_datetime(
        dust_df["Date (YYYYMMDD)"].astype(str) + dust_df["time_str"],
        format="%Y%m%d%H%M",
        utc=True,
        errors="coerce"
    )

    n_before = len(dust_df)
    dust_df = dust_df.dropna(subset=["datetime"]).copy()
    n_after = len(dust_df)
    n_removed = n_before - n_after
    print(f"Removed {n_removed} dust events due to invalid datetime parsing.")

    dust_df["datetime"] = (
        dust_df["datetime"]
        .dt.tz_convert(None)
    )
    return dust_df

def create_non_dust_df(dust_df):
    '''
    Create dataframe of dust source locations when they are not actively blowing dust in 2001-2020. 
    '''
    print("Creating the non-dust dataframe...")

    lat_lon = dust_df[["latitude", "longitude"]].drop_duplicates()
    dates = pd.date_range(start="2001-01-01", end="2020-12-31", freq="D")
    dust_dates = pd.to_datetime(dust_df["datetime"]).dt.normalize().unique()
    filtered_dates = dates[~dates.isin(dust_dates)]
    dates_df = pd.DataFrame({"date": filtered_dates})
    non_dust_df = lat_lon.merge(dates_df, how="cross")
    non_dust_df["datetime"] = pd.to_datetime(non_dust_df["date"])
    non_dust_df = non_dust_df.drop(columns="date")

    print(f"Non-dust dataframe: {np.shape(non_dust_df)}, from {len(filtered_dates)} non-dust days...")

    return non_dust_df

def nearest_grid_point(lat2d, lon2d, lat, lon):
    dist2 = (lat2d - lat)**2 + (lon2d - lon)**2
    iy, ix = np.unravel_index(np.argmin(dist2), dist2.shape)
    return iy, ix

def add_winds_to_dust_df(processed_wind_path, dust_df):

    if processed_wind_path.exists():
        print("Opening wind speed dataset...")
        ds_ws = xr.open_dataset(processed_wind_path)
    else:
        print("Wind speed data not found, exiting...")
        sys.exit()
    
    print("For each dust event, getting the wind speed...")

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

def open_gldas_file(gldas_path):
    ds = xr.open_dataset(gldas_path)
    return ds

def filter_to_region(ds, location_name):

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    filtered_ds = ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max)
    )
    return filtered_ds

def _get_coords_for_region(location_name):
    """
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    """
    locations = {
        "American Southwest": [(44, -128), (27.5, -100)],
        
        "Chihuahua": [(33.3, -110.0), (28.0, -105.3)],
        "West Texas": [(35.0, -104.0), (31.8, -100.5)],
        "Central High Plains": [(43.0, -105.0), (36.5, -98.0)],
        "Nevada": [(43.0, -120.7), (37.0, -114.5)],
        "Utah": [(42.0, -114.5), (37.5, -109.0)],
        "Southern California": [(37.0, -119.0), (30.0, -114.2)],
        "Four Corners": [(37.5, -112.5), (34.4, -107.0)],
        "San Luis Valley": [(38.5, -106.5), (37.0, -105.3)],

        "N Mexico 1": [(31.8, -107.6), (31.3, -107.1)],
        "Carson Sink": [(40.1, -118.75), (39.6, -118.25)],
        "N Mexico 2": [(31.4, -108.25), (30.9, -107.75)],
        "N Mexico 3": [(31.1, -107.15), (30.6, -106.65)],
        "Black Rock 1": [(41.15, -119.35), (40.65, -118.85)],
        "West Texas 1": [(32.95, -102.35), (32.45, -101.85)],
        "N Mexico 4": [(30.65, -107.65), (30.15, -107.15)],
        "N Mexico 5": [(31.0, -106.65), (30.5, -106.15)],
        "White Sands": [(33.15, -106.6), (32.65, -106.1)],
        "West Texas 2": [(33.5, -102.8), (33.0, -102.30)],
        "SLV2": [(38.05, -106.15), (37.55, -105.65)],
        "N Mexico 6": [(29.55, -107.05), (29.05, -106.55)],
        "NE AZ": [(35.7, -111.1), (35.2, -110.6)],
        "NW New Mexico": [(36.15, -108.85), (35.65, -108.35)],
        "Black Rock 2": [(40.75, -119.9), (40.25, -119.4)],
        "N Mexico 7": [(30.9, -108.15), (30.4, -107.65)],
    }
    coords = locations[location_name]
    lats = [p[0] for p in coords]
    lons = [p[1] for p in coords]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    return lat_min, lat_max, lon_min, lon_max

def add_moisture_to_dust_df(path_moisture_grid_dust_days, dust_df):

    print(f"Loading cached wldas data from {path_moisture_grid_dust_days}")
        #--- Seems to have some good default chunking scheme, 
        #--- gives me a warning when I try to implement my own
    moisture_dust_days = xr.open_dataset(path_moisture_grid_dust_days)

    print("Adding WLDAS moisture to dust dataframe...")

    moisture_dates = pd.to_datetime(moisture_dust_days.time.values).normalize()
    moisture_dates_set = set(moisture_dates.values)

    dust_df['moisture'] = None
    skipped_no_wldas_date = 0

    for idx, row in dust_df.iterrows():
        dust_time = row['datetime'].normalize()

        if dust_time.to_datetime64() not in moisture_dates_set:
            skipped_no_wldas_date += 1
            continue

        try:
            wldas_point = moisture_dust_days.sel(
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
    texture_ds = open_gldas_file(gldas_path)
    texture_ds = filter_to_region(texture_ds, location_name)
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
    min_lat, max_lat, min_lon, max_lon = _get_coords_for_region(location_name)
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