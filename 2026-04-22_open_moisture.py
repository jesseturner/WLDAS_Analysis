import xarray as xr

ds = xr.open_dataset("DATA/processed/6_moisture_data_2026-04-22.nc")
print(ds)