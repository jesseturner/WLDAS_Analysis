import os, requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import xarray as xr
import numpy as np

class WldasData:
    def __init__(self, date):
        self.date = date
        self.download_dir = Path("WLDAS_data")
        self._get_filepath()

    def _get_filepath(self):
        self.filepath = None
        date_str = self.date.strftime("%Y%m%d")
        matches = list(self.download_dir.glob(f"*{date_str}*"))
        if matches:
            self.filepath = str(matches[0])
            print(f"Found file: {self.filepath}")
        else:
            print(f"Run .download() to get file")
            print("Warning: WLDAS data files are large, each ~900 MB")

    def download(self):
        #--- Set .netrc with GES DISC username and password
        #--- Add a reminder if there is a no permissions error

        YYYY = self.date.strftime('%Y')
        MM = self.date.strftime('%m')
        DD = self.date.strftime('%d')

        url = f"https://hydro1.gesdisc.eosdis.nasa.gov/data/WLDAS/WLDAS_NOAHMP001_DA1.D1.0/{YYYY}/{MM}/WLDAS_NOAHMP001_DA1_{YYYY}{MM}{DD}.D10.nc"

        #--- Create session with NASA Earthdata login
        session = requests.Session()
        session.auth = (os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD"))

        #--- Make download directory
        self.download_dir.mkdir(parents=True, exist_ok=True)

        #--- Download file
        print(f"Connecting to {url}...")
        response = session.get(url, stream=True)
        print("Connection established. Starting download...")

        if response.status_code == 200:
            #--- Extract filename from content-disposition if present
            cd = response.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                filename = cd.split('filename=')[-1].strip('\"')
            else:
                filename = url.split('/')[-1]

            self.filepath = self.download_dir / filename

            #--- Write file to local disk
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192

            with open(self.filepath, 'wb') as f, tqdm(
                total=total_size, unit='B', unit_scale=True, desc=filename
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            print(f"Downloaded to {self.filepath}")
        else:
            print(f"Failed to download: {response.status_code} {response.reason}")
            print(response.text)

    def view_dataset(self):
        if self.filepath:
            ds = xr.open_dataset(self.filepath)
            print(ds)

    def view_variables(self):
        if self.filepath: 
            ds = xr.open_dataset(self.filepath)
            for var in ds.data_vars:
                print(var)

    def create_hist_for_variables(self):
        if self.filepath: 
            ds = xr.open_dataset(self.filepath)
            hist_store = {}  # Will hold {"variable_name": (counts, bin_edges)}

            for variable in ds.data_vars:
                data = ds[variable].values.flatten()

                # Skip non-numeric data types (e.g., datetime64, object)
                if not np.issubdtype(data.dtype, np.number):
                    print(f"Skipping variable '{variable}' of type {data.dtype}")
                    continue

                bin_edges = np.linspace(np.min(data), np.max(data), num=51)
                print(variable, " min/max: ",np.min(data), np.max(data))
                #counts, _ = np.histogram(data, bins=bin_edges)
                #hist_store[variable] = (counts, bin_edges)

            #print(hist_store)

            # Save periodically
            #np.savez(f"WLDAS_histograms/{variable}_hist.npz", counts=counts_total, bins=bin_edges)


    

