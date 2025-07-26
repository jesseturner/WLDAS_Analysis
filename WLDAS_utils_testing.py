from WLDAS_utils import WldasData
from datetime import datetime

wldas = WldasData(datetime(2001, 1, 12))

#wldas.download()

wldas.view_dataset()

wldas.view_variables()

wldas.create_hist_for_variables()
