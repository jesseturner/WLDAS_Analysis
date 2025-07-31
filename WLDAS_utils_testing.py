from WLDAS_utils import WldasData
from datetime import datetime

#--- Set up with values from (2002, 1, 2)
wldas = WldasData(datetime(2002, 1, 2), chunks={"lat": 300, "lon": 300}, print_vars=False)

#--- __init__
assert wldas.is_file_loaded(), "FAIL: File not loaded in __init__"
assert wldas.get_shape() == (1, 2787, 3591), f"FAIL: Unexpected shape {wldas.get_shape()}"
print("SUCCESS: __init__")

#--- filter_by_bounds
wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])
assert wldas.get_shape() == (1, 1650, 2493)
print("SUCCESS: filter_by_bounds")



#wldas.create_hist_for_variables(hist_name="all_data")
#wldas.create_hist_for_variables(hist_name="dust_points")


#wldas.plot_hist_for_variables(hist_name="dust_points")

