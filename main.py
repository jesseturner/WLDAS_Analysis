from WLDAS_utils import wldas_utils as wldas
from datetime import datetime

ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

ds = wldas.filter_by_bounds(ds, bounds=[27.5,44,-128,-100])

ds = wldas.filter_by_dust_points(ds, dust_path="Line_dust_data/dust_dataset_final_20241226.txt")

