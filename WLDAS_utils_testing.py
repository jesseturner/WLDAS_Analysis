from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2001, 1, 15), chunks={"lat": 300, "lon": 300}, bounds=[27.5,44,-128,-100])

#wldas.create_hist_for_variables(hist_name="dust_points")

#ldas.plot_hist_for_variables(hist_name="dust_points")
