#--- Creating NetCDF file with WLDAS soil moisture (coarsened) for full 2001-2020 domain
#------ Using dask dashboard to monitor progress

import xarray as xr
from datetime import datetime
import glob
import time
from dask.distributed import Client

def main():
    start = time.time()

    #--- Get moisture for date range
    wldas_path = "/mnt/data2/jturner/wldas_data"
    start_date = "20010101"
    end_date = "20210101"

    with Client(dashboard_address="127.0.0.1:8787") as client:
        print(client)
        #--- Combine and coarsen dataset
        moisture_dataset = create_moisture_dataset(wldas_path, start_date, end_date)

        #--- Save dataset
        print("Saving processed files as NetCDF...")
        timestamp = datetime.today().strftime("%Y-%m-%d")
        processed_wldas_path = f"DATA/processed/1_moisture_grid_{timestamp}.nc"
        print(moisture_dataset.chunks)
        moisture_dataset.to_netcdf(processed_wldas_path)
        print(f"Saved wldas set to {processed_wldas_path}")
    
    end = time.time()
    print(f"Time to process: {end - start:.2f} seconds")

    return

#------------------------

def create_moisture_dataset(wldas_path, start_date, end_date):
    print("Opening WLDAS files for each date...")

    start = datetime.strptime(start_date, "%Y%m%d")
    end = datetime.strptime(end_date, "%Y%m%d")

    files = glob.glob(f"{wldas_path}/WLDAS_NOAHMP001_DA1_*.nc.SUB.nc4")

    selected = []
    for f in files:
        date_str = f.split("_DA1_")[1][:8]
        file_date = datetime.strptime(date_str, "%Y%m%d")

        if start <= file_date <= end:
            selected.append(f)

    selected = sorted(selected)

    print(f"Combining {len(selected)} WLDAS files...")    
    wldas_dataset = xr.open_mfdataset(
        selected,
        combine="by_coords",
        drop_variables="time_bnds",
        chunks="auto",
    )

    wldas_dataset = wldas_dataset['SoilMoi00_10cm_tavg']
    wldas_dataset = wldas_dataset.chunk({"lon": 200, "lat": 200, "time": 100})

    #--- Coarsen resolution for wldas_set
    COARSEN_LAT = 24
    COARSEN_LON = 24
    wldas_dataset_coarse = (
        wldas_dataset
        .coarsen(lat=COARSEN_LAT, lon=COARSEN_LON, boundary="trim")
        .mean()
    )

    return wldas_dataset_coarse

#------------------------

if __name__ == "__main__":
    main()