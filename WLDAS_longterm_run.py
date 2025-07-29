from WLDAS_utils import WldasData
from datetime import datetime, timedelta
import os

start_date = datetime(2001, 2, 1)
end_date = datetime(2001, 12, 31)

current_date = start_date

while current_date <= end_date:
    wldas = WldasData(current_date, chunks={"lat": 300, "lon": 300})
    is_data = wldas.get_data()
    
    if is_data: 
        wldas.filter_by_bounds(bounds=[27.5,44,-128,-100])

        wldas.create_hist_for_variables(hist_name="all_data")
        wldas.create_hist_for_variables(hist_name="dust_points")

        #--- Delete WLDAS data
        file_path = f"WLDAS_data/WLDAS_NOAHMP001_DA1_{current_date.strftime('%Y%m%d')}.D10.nc"
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print("File not found.")
    
    current_date += timedelta(days=1)

