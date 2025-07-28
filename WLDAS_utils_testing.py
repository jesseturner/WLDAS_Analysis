from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2001, 1, 15), chunks={"lat": 300, "lon": 300})

#wldas.create_hist_for_variables(hist_name="all_data")

wldas.plot_hist_for_variables(hist_name="all_data")
