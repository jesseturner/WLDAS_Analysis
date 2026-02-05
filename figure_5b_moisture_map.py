
from pathlib import Path
import xarray as xr
import sys


# Paths for cached datasets
processed_wldas_total_path = Path("data/processed/wldas_sample/wldas_total.nc")
processed_wldas_dust_path = Path("data/processed/wldas_sample/wldas_dust.nc")

print("Getting cached WLDAS datasets...")
if processed_wldas_total_path.exists() and processed_wldas_dust_path.exists():
    wldas_total = xr.open_dataset(processed_wldas_total_path)
    wldas_dust = xr.open_dataset(processed_wldas_dust_path)
else:
    print("Missing a cached file, run figure_5a to create them.")
    sys.exit()

print(wldas_total)
print(wldas_dust)

