from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2001, 1, 9))

wldas.download()