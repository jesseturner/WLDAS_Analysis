from WLDAS_utils import WldasData
from datetime import datetime
import glob, os

#--- Set up with values from (2002, 1, 2)
wldas = WldasData(datetime(2002, 1, 2), chunks={"lat": 300, "lon": 300}, print_vars=False, print_ds=False)

#--- __init__
assert wldas.is_file_loaded(), "FAIL: File not loaded in __init__"
assert wldas.get_shape() == (1, 2787, 3591), f"FAIL: Unexpected shape {wldas.get_shape()}"
print("SUCCESS: __init__")

#--- filter_by_bounds
wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])
assert wldas.get_shape() == (1, 1650, 2493)
print("SUCCESS: filter_by_bounds")

#--- create_hist_for_variables
wldas.create_hist_for_variables(hist_name="test")
assert os.path.isfile("WLDAS_hist/test_20020102.pkl")
print("SUCCESS: create_hist_for_variables")

#--- plot_hist_for_variables
wldas.plot_hist_for_variables(hist_name="test")
assert len(glob.glob("WLDAS_hist_plots/test*")) == 41
print("SUCCESS: plot_hist_for_variables")

#--- delete created files
for file_path in glob.glob("WLDAS_hist_plots/test*"):
    os.remove(file_path)