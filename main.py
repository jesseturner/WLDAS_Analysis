from WLDAS_utils import wldas_utils as wldas
from Line_dust_data import line_dust_utils as dust

dust_path="Line_dust_data/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

#ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

#ds = wldas.filter_by_bounds(ds, bounds=[27.5,44,-128,-100])

#ds = wldas.filter_by_dust_points(ds, dust_df)

#ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")

#ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")

wldas_path = "/mnt/data2/jturner/wldas_data"
plus_minus_30_dir = "WLDAS_plus_minus_30"

# filepath = f"{wldas_path}/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"
# ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)

# wldas.get_wldas_plus_minus_30(dust_df, wldas_path, plus_minus_30_dir)

# json_filepath = "WLDAS_plus_minus_30/20021217_1845_lat3041_lon10653.json"
# wldas.plot_wldas_plus_minus_30(json_filepath, "WLDAS_plus_minus_30_plots")

print(dust_df)

dust_df_region = dust.filter_to_region(dust_df, location_name="Chihuahua")
print(dust_df_region)
