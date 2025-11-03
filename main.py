from WLDAS_utils import wldas_utils as wldas
from Line_dust_data import line_dust_utils as dust

dust_path="Line_dust_data/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

#ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

#ds = wldas.filter_by_bounds(ds, bounds=[27.5,44,-128,-100])

#ds = wldas.filter_by_dust_points(ds, dust_df)

#ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")

#ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")


dust_path = "Line_dust_data/dust_dataset_final_20241226.txt"
wldas_path = "/mnt/data2/jturner/wldas_data"
plus_minus_30_dir = "WLDAS_plus_minus_30"

# filepath = f"{wldas_path}/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"
# ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)

# wldas.get_wldas_plus_minus_30(dust_df, wldas_path, plus_minus_30_dir)

# json_filepath = "WLDAS_plus_minus_30/20021217_1845_lat3041_lon10653.json"
#wldas.plot_wldas_plus_minus_30(json_filepath, "WLDAS_plus_minus_30_plots")

#--- Print out code to run for each location:
locations = {
    "Chihuahua": [(33.3, -110.0), (28.0, -105.3)],
    "West Texas": [(35.0, -104.0), (31.8, -100.5)],
    "Central High Plains": [(43.0, -105.0), (36.5, -98.0)],
    "Nevada": [(43.0, -120.7), (37.0, -114.5)],
    "Utah": [(42.0, -114.5), (37.5, -109.0)],
    "Southern California": [(37.0, -119.0), (30.0, -114.2)],
    "Four Corners": [(37.5, -112.5), (34.4, -107.0)],
    "San Luis Valley": [(38.5, -106.5), (37.0, -105.3)],

    # "N Mexico 1": [(31.8, -107.6), (31.3, -107.1)],
    # "Carson Sink": [(40.1, -118.75), (39.6, -118.25)],
    # "N Mexico 2": [(31.4, -108.25), (30.9, -107.75)],
    # "N Mexico 3": [(31.1, -107.15), (30.6, -106.65)],
    # "Black Rock 1": [(41.15, -119.35), (40.65, -118.85)],
    # "West Texas 1": [(32.95, -102.35), (32.45, -101.85)],
    # "N Mexico 4": [(30.65, -107.65), (30.15, -107.15)],
    # "N Mexico 5": [(31.0, -106.65), (30.5, -106.15)],
    # "White Sands": [(33.15, -106.6), (32.65, -106.1)],
    # "West Texas 2": [(33.5, -102.8), (33.0, -102.30)],
    # "SLV2": [(38.05, -106.15), (37.55, -105.65)],
    # "N Mexico 6": [(29.55, -107.05), (29.05, -106.55)],
    # "NE AZ": [(35.7, -111.1), (35.2, -110.6)],
    # "NW New Mexico": [(36.15, -108.85), (35.65, -108.35)],
    # "Black Rock 2": [(40.75, -119.9), (40.25, -119.4)],
    # "N Mexico 7": [(30.9, -108.15), (30.4, -107.65)],
}

wldas.get_wldas_plus_minus_30_average(plus_minus_30_dir)
wldas.plot_wldas_plus_minus_30_average("WLDAS_plus_minus_30_average/average_american_southwest.json", "WLDAS_plus_minus_30_plots_average")

# for name, ((lat_max, lon_min), (lat_min, lon_max)) in locations.items():
#     boundary_box = [lat_min, lon_min, lat_max, lon_max]
#     print(
#         f'wldas.get_wldas_plus_minus_30_average("WLDAS_plus_minus_30", boundary_box={boundary_box}, location_str="{name}")'
#     )
#     location_str_name = name.lower().replace(" ", "_")
#     print(
#         f'wldas.plot_wldas_plus_minus_30_average_std("WLDAS_plus_minus_30_average/average_{location_str_name}.json", "WLDAS_plus_minus_30_average/std_{location_str_name}.json", "WLDAS_plus_minus_30_plots_average_std", location_str="{name}")'
#     )

# wldas.plot_wldas_plus_minus_30_average_all("WLDAS_plus_minus_30_average/big_regions/","WLDAS_plus_minus_30_plots_all", ylim=None)

