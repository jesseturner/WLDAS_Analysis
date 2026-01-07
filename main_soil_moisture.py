from modules_soil_moisture import utils_downloading as wldas_dl
from modules_soil_moisture import utils_processing as wldas_proc
from modules_soil_moisture import utils_plotting as wldas_plot
from modules_line_dust import line_dust_utils as dust
from modules_timing import timing_functions as time


#--- Downloading WLDAS
#------ Primary method is a subset download described in data/readme.md
# from datetime import datetime
# wldas_dl.get_wldas_data(date=datetime(2021, 12, 6), download_dir="z_temp")

from pathlib import Path
import random

time.time_all_functions(wldas_proc)
time.time_all_functions(wldas_plot)

#--- Sample the WLDAS data
wldas_path = "/mnt/data2/jturner/wldas_data"
file_dir = Path(wldas_path)
file_sample = random.sample(list(file_dir.glob("*.nc4")), 300)

#--- Load files in xarray dataset
ds = wldas_proc.open_wldas_files_as_xarray_ds(file_sample)
ds = wldas_proc.filter_by_bounds(ds, location_name="American Southwest")

#--- Filter moisture dataset to dust-producing regions
dust_path="data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
ds_dust_ever = wldas_proc.filter_by_ever_dust_points(ds, dust_df)
# ds_dust_current = wldas_proc.filter_by_current_dust_points(ds, dust_df)

#--- Plot the average soil moisture
#------ Reduce resolution for faster plotting
# ds_low_res = ds.isel(lat=slice(0, None, 10), lon=slice(0, None, 10))
# ds_dust_low_res = ds_dust_ever.isel(lat=slice(0, None, 10), lon=slice(0, None, 10))

# wldas_plot.plot_map_avg_moisture(ds_low_res, 
#                                  fig_title="Average soil moisture", 
#                                  location="American Southwest",
#                                  fig_dir="figures", 
#                                  fig_name="ex_average_soil_moisture")
# wldas_plot.plot_map_avg_moisture(ds_dust_low_res, 
#                                  fig_title="Average soil moisture (dust sources)", 
#                                  location="American Southwest",
#                                  fig_dir="figures", 
#                                  fig_name="ex_average_soil_moisture_dust")

#--- Plot histogram comparison between dust and all moisture measurements
wldas_plot.hist_comparison_plot(ds, ds_dust_ever)
# wldas_plot.hist_comparison_stats(ds, ds_dust_ever)