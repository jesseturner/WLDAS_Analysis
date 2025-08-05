from pathlib import Path
import requests, os, sys
from tqdm import tqdm
import xarray as xr

def get_wldas_data(date, chunks=None, print_vars=False, print_ds=False):
        download_dir = Path("WLDAS_data")
        filepath = _get_local_wldas(date, download_dir)
        if not filepath:
            filepath = _run_download_wldas(date, download_dir)
        if filepath:
            ds = _load_data_with_xarray(filepath, chunks, print_vars, print_ds)
        else: 
            print("No data found locally or at download link.")
            ds = None
        
        return ds

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

def _load_data_with_xarray(filepath, chunks, print_vars, print_ds):
        if filepath:
            try:
                ds = xr.open_dataset(filepath, chunks=chunks)
                if print_ds: print(ds)
                if print_vars: 
                    for var in ds.data_vars:
                        print(f"{var} => {ds[var].attrs.get("standard_name")}, {ds[var].attrs.get("long_name")}, units = {ds[var].attrs.get("units")}")
            except (FileNotFoundError, OSError) as e:
                print(f"Could not open dataset at {filepath}: {e}")
        return ds

def filter_by_bounds(ds, bounds=None):
    if not isinstance(bounds, list) or len(bounds) != 4:
        print("Bounds must be a list of four coordinates: [Latitude South, Latitude North, Longitude West, Longitude East]")
        return
    ds = ds.sel(
        lat=slice(bounds[0], bounds[1]),
        lon=slice(bounds[2], bounds[3]))
    return ds