import requests, os, sys
from tqdm import tqdm
from pathlib import Path

def get_wldas_data(date, download_dir):
    '''
    Downloading individual WLDAS files. Alternative to the preferred bulk subset described in data/readme.md. 
    Data only available within 1979-2023. 
    Must have .netrc set with GES DISC username and password

    Date: datetime(2021, 1, 6)
    '''
    filepath = _get_local_wldas(date, download_dir)
    if not filepath:
        filepath = _run_download_wldas(date, download_dir)
    if filepath:
        print(f"Successfully downloaded: {filepath}")
    else: 
        print("No data found locally or at download link.")
    
    return

def _get_local_wldas(date, download_dir):
    '''
    Used within get_wldas_data()
    '''
    date_str = date.strftime("%Y%m%d")
    matches = list(Path(download_dir).glob(f"*{date_str}*"))
    if matches:
        filepath = str(matches[0])
        print(f"Found file: {filepath}")
    else: filepath = None
    return filepath

def _run_download_wldas(date, download_dir):
    '''
    Used within get_wldas_data()
    '''
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
    Path(download_dir).mkdir(parents=True, exist_ok=True)

    filepath = _download_wldas(session, url, download_dir)
    return filepath

def _download_wldas(session, url, download_dir):
    '''
    Used within get_wldas_data()
    '''
    print(f"Connecting to {url}...")
    response = session.get(url, stream=True)
    print("Connection established. Starting download...")

    if response.status_code == 200:

        filename = _extract_filename(response, url)
        filepath = Path(download_dir) / Path(filename)
        _write_file_to_local_disk(response, filepath, filename)

        print(f"Downloaded to {filepath}")
    else:
        print(f"Failed to download: {response.status_code} {response.reason}")
        print(response.text)

    return filepath

def _extract_filename(response, url):
    '''
    Used within get_wldas_data()
    '''
    cd = response.headers.get('content-disposition')
    if cd and 'filename=' in cd:
        filename = cd.split('filename=')[-1].strip('\"')
    else:
        filename = url.split('/')[-1]
    return filename
    
def _write_file_to_local_disk(response, filepath, filename):
    '''
    Used within get_wldas_data()
    '''
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

