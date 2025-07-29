import os, requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm
import xarray as xr
import numpy as np
import pickle
import matplotlib.pyplot as plt
import pandas as pd

class WldasData:
    def __init__(self, date, engine=None, chunks=None):
        self.date = date
        self.download_dir = Path("WLDAS_data")
        self.engine = engine
        self.chunks = chunks
        self.ds = None
        self._get_filepath()

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

    def get_data(self, view_vars=False):
        success = False
        if self.filepath:
            try:
                self.ds = xr.open_dataset(self.filepath, engine=self.engine, chunks=self.chunks)
                print(self.ds)
                if view_vars: 
                    for var in self.ds.data_vars:
                        print(f"{var} => {self.ds[var].attrs.get("standard_name")}, {self.ds[var].attrs.get("long_name")}, units = {self.ds[var].attrs.get("units")}")
                success = True
            except (FileNotFoundError, OSError) as e:
                print(f"Could not open dataset at {self.filepath}: {e}")
        return success
                

    def filter_by_bounds(self, bounds=None):
        if not isinstance(bounds, list) or len(bounds) != 4:
            print("Bounds must be a list of four coordinates: [Latitude South, Latitude North, Longitude West, Longitude East]")
            return
        self.bounds = bounds
        self.ds = self.ds.sel(
            lat=slice(self.bounds[0], self.bounds[1]),
            lon=slice(self.bounds[2], self.bounds[3]))
            
    def get_shape(self):
        first_var_name = list(self.ds.data_vars)[0]
        shape = self.ds[first_var_name].shape
        print(f"Shape of dataset: {shape}")

    def create_hist_for_variables(self, hist_name=None):
        hist_store = {}  # Will hold {"variable_name": (counts, bin_edges)}

        if hist_name == None: 
            print("Running histograms for full dataset.")
            print("Options: all_data, dust_points")
            hist_name = "all_data"

        dataset = self.ds # Use all data by default

        #--- considering separating out this logic
        if hist_name == "dust_points":
            dataset = self._filter_by_dust_points()

        for variable in dataset.data_vars:
            data = dataset[variable].values.flatten()
            data = data[np.isfinite(data)]

            # Skip non-numeric data types (e.g., datetime64, object)
            if not np.issubdtype(data.dtype, np.number):
                print(f"Skipping variable '{variable}' of type {data.dtype}")
                continue

            long_name = dataset[variable].attrs.get("long_name")
            units = dataset[variable].attrs.get("units")
            bin_edges = np.linspace(np.nanmin(data), np.nanmax(data), num=51)
            counts, _ = np.histogram(data, bins=bin_edges)
            hist_store[variable] = (long_name, units, counts, bin_edges)

            os.makedirs("WLDAS_hist", exist_ok=True)
            with open(f"WLDAS_hist/{hist_name}_{self.date.strftime('%Y%m%d')}.pkl", "wb") as f:
                pickle.dump(hist_store, f)


    def plot_hist_for_variables(self, hist_name):
        with open(f"WLDAS_hist/{hist_name}_{self.date.strftime('%Y%m%d')}.pkl", "rb") as f:
            hist_store = pickle.load(f)
        os.makedirs("WLDAS_hist_plots", exist_ok=True)
        for variable in self.ds.data_vars:
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
            plt.savefig(f"WLDAS_hist_plots/{hist_name}_{variable}.png")
            plt.close()

    def _filter_by_dust_points(self):
        #--- WLDAS dataset within a range of any point that has ever been a dust source

        #--- Read dust data into a dataframe
        file_path = 'dust_dataset_final_20241226.txt'
        dust_df = pd.read_csv(file_path, sep=r'\s+', skiprows=2, header=None)
        dust_df.columns = ['Date (YYYYMMDD)', 'start time (UTC)', 'latitude', 'longitude', 'Jesse Check']

        #--- Clean lat/lon data
        dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
        dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')
        dust_df = dust_df.dropna(subset=['latitude', 'longitude'])

        #--- Set range from each dust source
        buffer_deg = 0.1

        #--- Initialize empty mask
        lat = self.ds['lat']
        lon = self.ds['lon']
        mask = xr.zeros_like(lat * 0 + lon * 0, dtype=bool)

        #--- Create mask with boxes around each dust point
        for point_lat, point_lon in zip(dust_df['latitude'], dust_df['longitude']):
            lat_mask = (lat >= point_lat - buffer_deg) & (lat <= point_lat + buffer_deg)
            lon_mask = (lon >= point_lon - buffer_deg) & (lon <= point_lon + buffer_deg)
            # Use broadcasting to apply lat/lon condition over grid
            point_mask = lat_mask & lon_mask
            mask = mask | point_mask
        
        #--- Apply mask to WLDAS dataset
        masked_ds = self.ds.where(mask, drop=True)

        return masked_ds




    

