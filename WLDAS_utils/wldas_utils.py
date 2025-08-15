from pathlib import Path
import requests, os, sys, pickle, json, re
from tqdm import tqdm
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from Line_dust_utils import line_dust_utils as dust
from datetime import datetime, timedelta

def get_wldas_data(date, chunks=None, print_vars=False, print_ds=False):
        download_dir = Path("WLDAS_data")
        filepath = _get_local_wldas(date, download_dir)
        if not filepath:
            filepath = _run_download_wldas(date, download_dir)
        if filepath:
            ds = load_data_with_xarray(filepath, chunks, print_vars, print_ds)
        else: 
            print("No data found locally or at download link.")
            ds = None
        
        return ds

def get_wldas_data_bulk_subset():
    print("Instructions: This is done through NASA DISC.")
    print("1. https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS")
    print("2. Subset directory")
    print("3. Download list of links")
    print("4. Earthdata authentication:")
    print("     .netrc with username and password")
    print("     .urs_cookies created")
    print("     .dodsrc with path to cookies and netrc")
    print("5. Add subset text file to directory <url.txt>")
    print("6. wget --load-cookies ~/.urs_cookies --save-cookies ~/.urs_cookies --keep-session-cookies --content-disposition -i '<url.txt>'")
    return

def _get_local_wldas(date, download_dir):
    date_str = date.strftime("%Y%m%d")
    matches = list(download_dir.glob(f"*{date_str}*"))
    if matches:
        filepath = str(matches[0])
        print(f"Found file: {filepath}")
    else: filepath = None
    return filepath

def _run_download_wldas(date, download_dir):
    #--- Set .netrc with GES DISC username and password
    #--- Add a reminder if there is a "no permissions" error

    YYYY = date.strftime('%Y')
    MM = date.strftime('%m')
    DD = date.strftime('%d')

    url = f"https://hydro1.gesdisc.eosdis.nasa.gov/data/WLDAS/WLDAS_NOAHMP001_DA1.D1.0/{YYYY}/{MM}/WLDAS_NOAHMP001_DA1_{YYYY}{MM}{DD}.D10.nc"

    #--- Create session with NASA Earthdata login
    session = requests.Session()
    session.auth = (os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD"))

    #--- Make download directory
    download_dir.mkdir(parents=True, exist_ok=True)

    filepath = _download_wldas(session, url, download_dir)
    return filepath

def _download_wldas(session, url, download_dir):
    print(f"Connecting to {url}...")
    response = session.get(url, stream=True)
    print("Connection established. Starting download...")

    if response.status_code == 200:

        filename = _extract_filename(response, url)
        filepath = download_dir / filename
        _write_file_to_local_disk(response, filepath, filename)

        print(f"Downloaded to {filepath}")
    else:
        print(f"Failed to download: {response.status_code} {response.reason}")
        print(response.text)

    return filepath

def _extract_filename(response, url):
    cd = response.headers.get('content-disposition')
    if cd and 'filename=' in cd:
        filename = cd.split('filename=')[-1].strip('\"')
    else:
        filename = url.split('/')[-1]
    return filename
    
def _write_file_to_local_disk(response, filepath, filename):
    total_size = int(response.headers.get('content-length', 0))
    chunk_size = 8192

    use_tqdm = sys.stderr.isatty() # Only use progress bar for in commandline
    with open(filepath, 'wb') as f, tqdm(
        total=total_size, unit='B', unit_scale=True, desc=filename, disable=not use_tqdm
    ) as pbar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    return

def load_data_with_xarray(filepath, chunks, print_vars, print_ds):
        if filepath:
            try:
                ds = xr.open_dataset(filepath, chunks=chunks)
                if print_ds: print(ds)
                if print_vars: 
                    for var in ds.data_vars:
                        print(f"{var} => {ds[var].attrs.get("standard_name")}, {ds[var].attrs.get("long_name")}, units = {ds[var].attrs.get("units")}")
            except (FileNotFoundError, OSError) as e:
                print(f"Could not open dataset at {filepath}: {e}")
                ds = None
        return ds

def filter_by_bounds(ds, bounds=None):
    if not isinstance(bounds, list) or len(bounds) != 4:
        print("Bounds must be a list of four coordinates: [Latitude South, Latitude North, Longitude West, Longitude East]")
        return
    ds = ds.sel(
        lat=slice(bounds[0], bounds[1]),
        lon=slice(bounds[2], bounds[3]))
    return ds

def filter_by_dust_points(ds, dust_path):
    #--- WLDAS dataset within a range of any point that has ever been a dust source

    dust_df = dust._read_dust_data_into_df(dust_path)

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

def plot_hist_for_variables(ds, hist_dir):
    date = _datetime_from_xarray_date(ds.time)
    
    with open(f"{hist_dir}/{date.strftime('%Y%m%d')}.pkl", "rb") as f:
        hist_store = pickle.load(f)
    os.makedirs(f"{hist_dir}", exist_ok=True)
    for variable in ds.data_vars:
        if variable not in hist_store:
            print(f"Skipping '{variable}' — no histogram stored.")
            continue

        long_name, units, counts, bin_edges = hist_store[variable]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        plt.figure(figsize=(8, 4))
        plt.bar(bin_centers, counts, width=np.diff(bin_edges), align="center", edgecolor="blue", color='blue', alpha=0.7,)
        plt.title(f"Histogram of {variable} ({long_name})")
        plt.xlabel(f"{units}")
        plt.ylabel("Frequency")
        plt.tight_layout()
        plt.savefig(f"{hist_dir}/{variable}.png")
        plt.close()

def _datetime_from_xarray_date(xarray_time):
    #--- grabbing the first time
    dt = xarray_time.values[0].astype('datetime64[ms]').astype('O')
    return dt

def get_wldas_plus_minus_30(dust_path, wldas_path, plus_minus_30_dir):
#--- For each dust case, get the WLDAS soil moisture for that location
#--- over the timespan from 30 days before to 30 days after
    wldas_path = Path(wldas_path)
    dust_df = dust._read_dust_data_into_df(dust_path)
    for index, row in dust_df.head(100).iterrows():
        date = str(row['Date (YYYYMMDD)'])
        time = str(int(row['start time (UTC)']))
        lat = str(row['latitude'])
        lon = str(row['longitude'])

        plus_minus_30_list = _loop_through_plus_minus_30(date, wldas_path, lat, lon)
        _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, lat, lon, date, time)


def _loop_through_plus_minus_30(date, wldas_path, lat, lon):
    base_date = datetime.strptime(date, "%Y%m%d")
    plus_minus_30_list = []
    for offset in range(-30, 31):
        date_i = base_date + timedelta(days=offset)
        date_i_str = datetime.strftime(date_i, "%Y%m%d")
        wldas_filepath = wldas_path / f"WLDAS_NOAHMP001_DA1_{date_i_str}.D10.nc.SUB.nc4"
        ds = load_data_with_xarray(wldas_filepath, chunks=None, print_vars=False, print_ds=False)
        #--- filter by lat lon
        if ds: 
            ds_point = ds.sel(lat=lat, lon=lon, method="nearest")
            ds_point_value = float(ds_point['SoilMoi00_10cm_tavg'].values[0])
            if ds_point_value:
                plus_minus_30_list.append(ds_point_value)
            else: 
                plus_minus_30_list.append(np.nan)
        else: 
            plus_minus_30_list.append(np.nan)

    return plus_minus_30_list

def _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, lat, lon, date, time):
    os.makedirs(plus_minus_30_dir, exist_ok=True)
    lat_clean = lat.replace(".", "")
    lon_clean = lon.replace("-", "").replace(".", "")
    with open(f"{plus_minus_30_dir}/{date}_{time}_lat{lat_clean}_lon{lon_clean}.json", "w") as f:
        json.dump(plus_minus_30_list, f)
    return

def plot_wldas_plus_minus_30(json_filepath, plot_dir):
    with open(json_filepath, "r") as f:
        plus_minus_30_list = json.load(f)
    
    # Get features from filename
    m = re.search(r'(\d{8})_(\d{4})_lat(\d+)_lon(\d+)', json_filepath)
    if m:
        date_str, time_str, lat_str, lon_str = m.groups()
        formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:]}"
        lat = int(lat_str) / 100
        lon = -int(lon_str) / 100
        formatted_coords = f"({lat:.2f}, {lon:.2f})"

    plt.figure(figsize=(8, 4))
    plt.plot(plus_minus_30_list, color='0', marker='o')
    plt.title(f"{formatted_date} {formatted_coords}")
    plt.xlabel("Days From Dust Event")
    plt.xticks(np.arange(0, 61, 3), labels=np.arange(-30, 31, 3))
    plt.ylabel("Soil Moisture (m$^3$/m$^3$)")
    plt.tight_layout()
    
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(f"{plot_dir}/{date_str}_{time_str}_{lat_str}_{lon_str}.png")
    plt.close()