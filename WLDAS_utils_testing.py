from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2001, 1, 15), chunks={"lat": 300, "lon": 300})
wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])
wldas.get_shape()

#wldas.create_hist_for_variables(hist_name="all_data")
#wldas.plot_hist_for_variables(hist_name="all_data")

#wldas._filter_by_dust_points()
wldas.create_hist_for_variables(hist_name="dust_points")
wldas.plot_hist_for_variables(hist_name="dust_points")
