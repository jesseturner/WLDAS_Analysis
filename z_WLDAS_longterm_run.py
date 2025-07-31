from WLDAS_utils import WldasData
from datetime import datetime, timedelta
import os

start_date = datetime(2001, 2, 1)
end_date = datetime(2001, 12, 31)

current_date = start_date

while current_date <= end_date:
    wldas = WldasData(current_date, chunks={"lat": 300, "lon": 300})
    
    if wldas.is_loaded():
        wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])

        wldas.create_hist_for_variables(hist_name="all_data")
        wldas.create_hist_for_variables(hist_name="dust_points")

        wldas.delete_file()
    
    current_date += timedelta(days=1)

