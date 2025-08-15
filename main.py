from WLDAS_utils import wldas_utils as wldas
from datetime import datetime

#ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

#ds = wldas.filter_by_bounds(ds, bounds=[27.5,44,-128,-100])

#ds = wldas.filter_by_dust_points(ds, dust_path="Line_dust_data/dust_dataset_final_20241226.txt")

#ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")

#ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")

filepath = "WLDAS_download/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"

ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)
