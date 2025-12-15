from soil_moisture_WLDAS import wldas_utils as moist
from line_dust_data import line_dust_utils as dust

#--- open soil moisture subset files
moist.create_moist_histogram(dir_path="/mnt/data2/jturner/wldas_data/")

#--- Relate WLDAS soil moisture to dust data
dust_path="line_dust_data/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_region_df = dust.filter_to_region(dust_df, location_name="American Southwest")
# print(dust_region_df)