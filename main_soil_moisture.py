from modules_soil_moisture import wldas_utils as moist
from modules_line_dust import line_dust_utils as dust

#--- open soil moisture subset files
wldas_path = "/mnt/data2/jturner/wldas_data/"
moist.create_moist_histogram(dir_path=wldas_path)

#--- Relate WLDAS soil moisture to dust data
dust_path="data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_region_df = dust.filter_to_region(dust_df, location_name="American Southwest")
# ds = wldas.filter_by_dust_points(ds, dust_df)
# ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")
# ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")

#--- WLDAS soil moisture time series before and after dust events
# plus_minus_30_dir = "data/processed/WLDAS_plus_minus_30"
# filepath = f"{wldas_path}/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"
# ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)
# wldas.get_wldas_plus_minus_30(dust_df, wldas_path, plus_minus_30_dir)
# json_filepath = "data/processed/WLDAS_plus_minus_30/20021217_1845_lat3041_lon10653.json"
# wldas.plot_wldas_plus_minus_30(json_filepath, "WLDAS_plus_minus_30_plots")

#--- Tracking WLDAS moisture patterns (total, yearly, frequency)
# fig_dir = "figures"
# save_dir = "data/processed/wldas_time_pattern"
# wldas.create_region_average_over_time(wldas_dir=wldas_path, location_name="Chihuahua", save_dir=save_dir)
# csv_path = f"{save_dir}/region_moisture_Chihuahua.csv"
# wldas.plot_region_average_over_time(csv_path, plot_dir=fig_dir, location_str="Chihuahua")
# wldas.plot_region_average_over_year(csv_path, dust_region_df=dust_region_df, plot_dir=fig_dir, location_str="Chihuahua")
# wldas.plot_frequency_analysis(csv_path, dust_region_df=dust_region_df, plot_dir=fig_dir, location_str="Chihuahua")