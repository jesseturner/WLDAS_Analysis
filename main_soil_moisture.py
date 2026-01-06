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
file_sample = random.sample(list(file_dir.glob("*.nc4")), 9)

#--- Load files in xarray dataset
ds = wldas_proc.load_mf_data_with_xarray(file_sample)
ds = wldas_proc.filter_by_bounds(ds, location_name="American Southwest")

#--- Filter moisture dataset to dust-producing regions
dust_path="data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
ds_dust = wldas_proc.filter_by_dust_points(ds, dust_df)

#--- Reduce resolution for faster plotting
ds_low_res = ds.isel(lat=slice(0, None, 10), lon=slice(0, None, 10))
ds_dust_low_res = ds_dust.isel(lat=slice(0, None, 10), lon=slice(0, None, 10))


#--- Plot the average soil moisture
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



#=======================
# Methods below are being improved
#=======================

#--- Relate WLDAS soil moisture to dust data
# dust_path="data/raw/line_dust/dust_dataset_final_20241226.txt"
# dust_df = dust.read_dust_data_into_df(dust_path)
# dust_region_df = dust.filter_to_region(dust_df, location_name="American Southwest")
# ds = wldas.filter_by_dust_points(ds, dust_df)
# ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")
# ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")

#--- WLDAS soil moisture time series before and after dust events
# plus_minus_30_dir = "data/processed/WLDAS_plus_minus_30"
# filepath = f"{wldas_path}/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"
# ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)
# wldas_plot.get_wldas_plus_minus_30(dust_df, wldas_path, "data/processed/WLDAS_plus_minus_30")
# json_filepath = "data/processed/WLDAS_plus_minus_30/20021217_1845_lat3041_lon10653.json"
# wldas_plot.plot_wldas_plus_minus_30(json_filepath, "WLDAS_plus_minus_30_plots")

#--- Tracking WLDAS moisture patterns (total, yearly, frequency)
# fig_dir = "figures"
# save_dir = "data/processed/wldas_time_pattern"
# wldas.create_region_average_over_time(wldas_dir=wldas_path, location_name="Chihuahua", save_dir=save_dir)
# csv_path = f"{save_dir}/region_moisture_Chihuahua.csv"
# wldas.plot_region_average_over_time(csv_path, plot_dir=fig_dir, location_str="Chihuahua")
# wldas.plot_region_average_over_year(csv_path, dust_region_df=dust_region_df, plot_dir=fig_dir, location_str="Chihuahua")
# wldas.plot_frequency_analysis(csv_path, dust_region_df=dust_region_df, plot_dir=fig_dir, location_str="Chihuahua")

#--- Plot processed histogram data
# total_hist = "data/processed/wldas_soil_moisture_hist_total"
# dust_hist = "data/processed/wldas_soil_moisture_hist_dust"
# moist.plot_hist_for_moisture(dust_hist)