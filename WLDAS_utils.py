import os, requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import xarray as xr
import numpy as np
import pickle
import matplotlib.pyplot as plt

class WldasData:
    def __init__(self, date, engine=None, chunks=None):
        self.date = date
        self.download_dir = Path("WLDAS_data")
        self.engine = engine
        self.chunks = chunks
        self._get_filepath()
        self._get_data(view_vars=True)

    def _get_filepath(self):
        self.filepath = None
        date_str = self.date.strftime("%Y%m%d")
        matches = list(self.download_dir.glob(f"*{date_str}*"))
        if matches:
            self.filepath = str(matches[0])
            print(f"Found file: {self.filepath}")
        else:
            print(f"Runing download to get file")
            print("Warning: WLDAS data files are large, each ~900 MB")
            self._download()

    def _download(self):
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

    def _get_data(self, view_vars=False):
        if self.filepath:
            self.ds = xr.open_dataset(self.filepath, engine=self.engine, chunks=self.chunks)
            print(self.ds)
        if view_vars: 
            for var in self.ds.data_vars:
                print(f"{var} => {self.ds[var].attrs.get("standard_name")}, {self.ds[var].attrs.get("long_name")}, units = {self.ds[var].attrs.get("units")}")

    def create_hist_for_variables(self, hist_name):
        hist_store = {}  # Will hold {"variable_name": (counts, bin_edges)}

        for variable in self.ds.data_vars:
            data = self.ds[variable].values.flatten()
            data = data[np.isfinite(data)]

            # Skip non-numeric data types (e.g., datetime64, object)
            if not np.issubdtype(data.dtype, np.number):
                print(f"Skipping variable '{variable}' of type {data.dtype}")
                continue

            bin_edges = np.linspace(np.nanmin(data), np.nanmax(data), num=51)
            counts, _ = np.histogram(data, bins=bin_edges)
            hist_store[variable] = (counts, bin_edges)

            os.makedirs("WLDAS_histograms", exist_ok=True)
            with open(f"WLDAS_histograms/{hist_name}.pkl", "wb") as f:
                pickle.dump(hist_store, f)

    def plot_histogram_for_variables(self, hist_name):
        with open(f"WLDAS_histograms/{hist_name}.pkl", "rb") as f:
            hist_store = pickle.load(f)
        for variable in self.ds.data_vars:
            if variable not in hist_store:
                print(f"Skipping '{variable}' — no histogram stored.")
                continue

            counts, bin_edges = hist_store[variable]
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

            plt.figure(figsize=(8, 4))
            plt.bar(bin_centers, counts, width=np.diff(bin_edges), align="center", edgecolor="black")
            plt.title(f"Histogram of {variable}")
            plt.xlabel("Value")
            plt.ylabel("Frequency")
            plt.tight_layout()
            plt.savefig(f"WLDAS_histograms/{hist_name}_{variable}.png")
            plt.close()



    

