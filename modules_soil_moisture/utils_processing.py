import os, pickle, json, re, glob
import xarray as xr
import numpy as np
from datetime import datetime, timedelta
import pandas as pd

def load_mf_data_with_xarray(file_list):
    '''
    Loads WLDAS data into an xarray dataset. 

    :param file_list: [str]
    '''

    ds = xr.open_mfdataset(file_list, combine='nested', concat_dim='time')
    ds = ds.drop_vars('time_bnds')
    ds.attrs.clear()
    ds = ds.sortby('time')

    return ds

def filter_by_bounds(ds, location_name="American Southwest"):
    '''
    Filters WLDAS xarray dataset to a specific region.
    
    :param ds: from load_data_with_xarray()
    :param location_name: str, options listed in _get_coords_for_region()
    '''

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    ds = ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max))
    return ds

def _get_coords_for_region(location_name):
    '''
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    '''
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

def filter_by_dust_points(ds, dust_df):
    """
    Returns a WLDAS dataset with values within a range of any point that has ever been a dust source.
    """

    #--- Set range from each dust source
    buffer_deg = 0.1

    #--- Initialize empty mask
    lat = ds['lat']
    lon = ds['lon']
    mask = xr.zeros_like(lat * 0 + lon * 0, dtype=bool)

    #--- Create mask with boxes around each dust point
    for point_lat, point_lon in zip(dust_df['latitude'], dust_df['longitude']):
        lat_mask = (lat >= point_lat - buffer_deg) & (lat <= point_lat + buffer_deg)
        lon_mask = (lon >= point_lon - buffer_deg) & (lon <= point_lon + buffer_deg)
        # Use broadcasting to apply lat/lon condition over grid
        point_mask = lat_mask & lon_mask
        mask = mask | point_mask
    
    #--- Apply mask to WLDAS dataset
    ds = ds.where(mask, drop=True)
    
    return ds

#==========================================
# Functions below are being improved
#==========================================

def create_hist_for_variables(ds, hist_dir):
    hist_store = {}  # Will hold {"variable_name": (counts, bin_edges)}

    for variable in ds.data_vars:
        data = ds[variable].values.flatten()
        data = data[np.isfinite(data)]

        # Skip non-numeric data types (e.g., datetime64, object)
        if not np.issubdtype(data.dtype, np.number):
            print(f"Skipping variable '{variable}' of type {data.dtype}")
            continue

        date = _datetime_from_xarray_date(ds.time)
        long_name = ds[variable].attrs.get("long_name")
        units = ds[variable].attrs.get("units")
        bin_edges = np.linspace(np.nanmin(data), np.nanmax(data), num=51)
        counts, _ = np.histogram(data, bins=bin_edges)
        hist_store[variable] = (long_name, units, counts, bin_edges)

        os.makedirs(hist_dir, exist_ok=True)
        with open(f"{hist_dir}/{date.strftime('%Y%m%d')}.pkl", "wb") as f:
            pickle.dump(hist_store, f)

    return ds

def _datetime_from_xarray_date(xarray_time):
    #--- grabbing the first time
    dt = xarray_time.values[0].astype('datetime64[ms]').astype('O')
    return dt

def get_wldas_plus_minus_30(dust_df, wldas_path, plus_minus_30_dir):
#--- For each dust case, get the WLDAS soil moisture for that location
#--- over the timespan from 30 days before to 30 days after
    wldas_path = wldas_path
    for index, row in dust_df.iterrows():
        print(f"Plus minus 30 for {index} of {len(dust_df)}")
        date = str(row['Date (YYYYMMDD)'])
        time = str(int(row['start time (UTC)']))
        lat = str(row['latitude'])
        lon = str(row['longitude'])

        plus_minus_30_list = _loop_through_plus_minus_30(date, wldas_path, lat, lon)

        lat_clean = lat.replace(".", "")
        lon_clean = lon.replace("-", "").replace(".", "")
        list_name = f"{date}_{time}_lat{lat_clean}_lon{lon_clean}"
        _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, list_name)
    return


def _loop_through_plus_minus_30(date, wldas_path, lat, lon):
    base_date = datetime.strptime(date, "%Y%m%d")
    plus_minus_30_list = []
    for offset in range(-30, 31):
        date_i = base_date + timedelta(days=offset)
        date_i_str = datetime.strftime(date_i, "%Y%m%d")
        wldas_filepath = wldas_path / f"WLDAS_NOAHMP001_DA1_{date_i_str}.D10.nc.SUB.nc4"
        ds = load_data_with_xarray(wldas_filepath, chunks=None, print_vars=False, print_ds=False)
        if ds: 
            ds_point_value = _filter_wldas_by_lat_lon(ds, lat, lon)
            if ds_point_value:
                plus_minus_30_list.append(ds_point_value)
            else: 
                plus_minus_30_list.append(np.nan)
        else: 
            plus_minus_30_list.append(np.nan)

    return plus_minus_30_list

def _filter_wldas_by_lat_lon(ds, lat, lon):
    ds_point = ds.sel(lat=lat, lon=lon, method="nearest")
    ds_point_soil_moisture = float(ds_point['SoilMoi00_10cm_tavg'].values[0])
    return ds_point_soil_moisture

def _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, list_name):
    os.makedirs(plus_minus_30_dir, exist_ok=True)

    if isinstance(plus_minus_30_list, np.ndarray):
        plus_minus_30_list = plus_minus_30_list.tolist()

    with open(f"{plus_minus_30_dir}/{list_name}.json", "w") as f:
        json.dump(plus_minus_30_list, f)
    return


def get_wldas_plus_minus_30_average(json_dir, boundary_box=[], location_str="American Southwest"):
    """
    boundary_box: [lat_min, lon_min, lat_max, lon_max]
    """

    file_list = glob.glob(f"{json_dir}/*.json")

    if boundary_box:
        file_list = _get_file_list_filtered_by_lat_lon(file_list, boundary_box)

    average_list, std_list = _average_json_files(file_list)

    plus_minus_30_dir = "WLDAS_plus_minus_30_average"
    location_str_save = location_str.lower().replace(" ", "_")
    average_list_name = f"average_{location_str_save}"
    std_list_name = f"std_{location_str_save}"
    _save_plus_minus_30_list(plus_minus_30_dir, average_list, average_list_name)
    _save_plus_minus_30_list(plus_minus_30_dir, std_list, std_list_name)

    return

def _average_json_files(file_list):
    all_data = []
    for file_path in file_list:
        with open(file_path, 'r') as f:
            try: 
                data = json.load(f)
            except Exception as e:
                print(f"Could not open json at {f}: {e}")
            all_data.append(data)

    all_data_array = np.array(all_data)
    average_list = np.nanmean(all_data_array, axis=0)
    std_list = np.nanstd(all_data_array, axis=0)
    return average_list, std_list

def _get_file_list_filtered_by_lat_lon(file_list, boundary_box):
    filtered_file_list = []
    lat_min, lon_min, lat_max, lon_max = boundary_box

    for f in file_list:
        lat, lon = _parse_lat_lon(f)
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            filtered_file_list.append(f)

    return filtered_file_list
        

def _parse_lat_lon(filename: str) -> tuple[float, float]:
    """
    Extract latitude and longitude from filename.
    Example: '..._lat3062_lon10797.json' -> (30.62, -107.97)
    """
    match = re.search(r"lat(\d+)_lon(\d+)", filename)
    if not match:
        raise ValueError(f"Could not parse lat/lon from {filename}")
    
    lat_str, lon_str = match.groups()
    lat = float(lat_str[:2] + "." + lat_str[2:])
    lon = -float(lon_str[:3] + "." + lon_str[3:])  # negative for west
    return lat, lon

def create_region_average_over_time(wldas_dir, location_name, save_dir):
    """
    Get average soil moistures for a region over the times in the WLDAS directory.
    """

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    dates = []
    moistures = []
    std = []
    file_list = glob.glob(os.path.join(wldas_dir, "*.nc4"))
    for count, filepath in enumerate(file_list, start=1):
        ds = load_data_with_xarray(os.path.join(wldas_dir,filepath))

        filtered_ds = ds.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        dt = filtered_ds.time
        moisture = filtered_ds["SoilMoi00_10cm_tavg"].mean(dim=['time', 'lat', 'lon'])
        moisture_std = filtered_ds["SoilMoi00_10cm_tavg"].std(dim=['time', 'lat', 'lon'])
        dates.append(dt[0].values)
        moistures.append(moisture.values)
        std.append(moisture_std.values)

        if count % 100 == 0:
            print(f"{count} / {len(file_list)}")

    region_moisture_df = pd.DataFrame({
        'moisture': moistures, 
        'standard deviation': std}, 
        index=dates
    )
    region_moisture_df.sort_index(inplace=True)

    region_moisture_df.to_csv(os.path.join(save_dir,f'region_moisture_{location_name}.csv'))

    return