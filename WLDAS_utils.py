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

            os.makedirs("WLDAS_histograms", exist_ok=True)
            with open(f"WLDAS_histograms/{hist_name}.pkl", "wb") as f:
                pickle.dump(hist_store, f)

    def plot_hist_for_variables(self, hist_name):
        with open(f"WLDAS_histograms/{hist_name}.pkl", "rb") as f:
            hist_store = pickle.load(f)
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
            plt.savefig(f"WLDAS_histograms/{hist_name}_{variable}.png")
            plt.close()

    def _filter_by_dust_points(self):
        #--- Read dust data into a dataframe
        file_path = 'dust_dataset_final_20241226.txt'
        dust_df = pd.read_csv(file_path, sep=r'\s+', skiprows=2, header=None)
        dust_df.columns = [
            'Date (YYYYMMDD)','start time (UTC)','latitude','longitude','Jesse Check'
        ]
        print(dust_df.head())

        #--- Create a mask of dust locations
        dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
        dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')

        #------ Define grid resolution
        lat_min, lat_max = self.bounds[0], self.bounds[1]
        lon_min, lon_max = self.bounds[2], self.bounds[3]

        #------ Create grid bins
        #------ 2 is 0.5 degree boxes, 10 is 0.1 degree boxes
        precision = 5
        lat_bins = np.arange(lat_min, lat_max + 1/precision, 1/precision)
        lon_bins = np.arange(lon_min, lon_max + 1/precision, 1/precision)

        mask = pd.DataFrame(index=lat_bins, columns=lon_bins, data=0)

        #------ Populate the mask (1 if a dust event occurred in the grid cell)
        for _, row in dust_df.iterrows():
            if (row['latitude'] < lat_max) & (row['latitude'] > lat_min) & (row['longitude'] < lon_max) & (row['longitude'] > lon_min):

                lat_idx = np.round(row['latitude'] * precision) / precision # Round to nearest bin (size set above)
                lon_idx = np.round(row['longitude'] * precision) / precision

                mask.loc[lat_idx, lon_idx] = 1  # Mark as a dust-affected cell
        
        ds = xr.open_dataset("WLDAS_nc_files/WLDAS_NOAHMP001_DA1_20010102.D10.nc")

        #--- Use `interp` to align NetCDF lat/lon with the mask
        mask_da = mask_da.interp(lat=ds.lat, lon=ds.lon, method="nearest")

        #--- Filter WLDAS data to dust zones

        # Apply mask using xarray.where()
        ds_filtered = ds.where(~np.isnan(mask_da), drop=True)

        return filtered_dataset



    

