from WLDAS_utils import wldas_utils as wldas
from datetime import datetime

ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

