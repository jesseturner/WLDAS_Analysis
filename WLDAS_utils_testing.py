from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2002, 1, 2), chunks={"lat": 300, "lon": 300}, view_vars=True)

if wldas.is_loaded(): 
    wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])
    wldas.get_shape()

#wldas.create_hist_for_variables(hist_name="all_data")
#wldas.create_hist_for_variables(hist_name="dust_points")


#wldas.plot_hist_for_variables(hist_name="dust_points")

