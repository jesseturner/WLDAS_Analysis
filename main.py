from WLDAS_utils import wldas_utils as wldas

#ds = wldas.get_wldas_data(datetime(2003, 1, 9), chunks={"lat": 300, "lon": 300}, print_vars=True, print_ds=True)

#ds = wldas.filter_by_bounds(ds, bounds=[27.5,44,-128,-100])

#ds = wldas.filter_by_dust_points(ds, dust_path="Line_dust_data/dust_dataset_final_20241226.txt")

#ds = wldas.create_hist_for_variables(ds, "WLDAS_hist_test")

#ds = wldas.plot_hist_for_variables(ds, "WLDAS_hist_test")


dust_path = "Line_dust_data/dust_dataset_final_20241226.txt"
wldas_path = "/mnt/data2/jturner/wldas_data"
plus_minus_30_dir = "WLDAS_plus_minus_30"

# filepath = f"{wldas_path}/WLDAS_NOAHMP001_DA1_20010112.D10.nc.SUB.nc4"
# ds = wldas.load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=True)

#wldas.get_wldas_plus_minus_30(dust_path, wldas_path, plus_minus_30_dir)

#json_filepath = "WLDAS_plus_minus_30/20040219_1730_lat3126_lon10689.json"
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

    "N Mexico 1": [(31.8, -107.6), (31.3, -107.1)],
    "Carson Sink": [(40.1, -118.75), (39.6, -118.25)],
    "N Mexico 2": [(31.4, -108.25), (30.9, -107.75)],
    "N Mexico 3": [(31.1, -107.15), (30.6, -106.65)],
    "Black Rock 1": [(41.15, -119.35), (40.65, -118.85)],
    "West Texas 1": [(32.95, -102.35), (32.45, -101.85)],
    "N Mexico 4": [(30.65, -107.65), (30.15, -107.15)],
    "N Mexico 5": [(31.0, -106.65), (30.5, -106.15)],
    "White Sands": [(33.15, -106.6), (32.65, -106.1)],
    "West Texas 2": [(33.5, -102.8), (33.0, -102.30)],
    "SLV2": [(38.05, -106.15), (37.55, -105.65)],
    "N Mexico 6": [(29.55, -107.05), (29.05, -106.55)],
    "NE AZ": [(35.7, -111.1), (35.2, -110.6)],
    "NW New Mexico": [(36.15, -108.85), (35.65, -108.35)],
    "Black Rock 2": [(40.75, -119.9), (40.25, -119.4)],
    "N Mexico 7": [(30.9, -108.15), (30.4, -107.65)],
}

# for name, ((lat_max, lon_min), (lat_min, lon_max)) in locations.items():
#     boundary_box = [lat_min, lon_min, lat_max, lon_max]
#     for is_std in (True, False):
#         print(
#             f'wldas.plot_wldas_plus_minus_30_average('
#             f'plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", '
#             f'is_std={is_std}, boundary_box={boundary_box}, location_str="{name}")'
#         )

#--- Delete this when done (printed out from before)
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True)
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False)

wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[28.0, -110.0, 33.3, -105.3], location_str="Chihuahua")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[28.0, -110.0, 33.3, -105.3], location_str="Chihuahua")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[31.8, -104.0, 35.0, -100.5], location_str="West Texas")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[31.8, -104.0, 35.0, -100.5], location_str="West Texas")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[36.5, -105.0, 43.0, -98.0], location_str="Central High Plains")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[36.5, -105.0, 43.0, -98.0], location_str="Central High Plains")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[37.0, -120.7, 43.0, -114.5], location_str="Nevada")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[37.0, -120.7, 43.0, -114.5], location_str="Nevada")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[37.5, -114.5, 42.0, -109.0], location_str="Utah")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[37.5, -114.5, 42.0, -109.0], location_str="Utah")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.0, -119.0, 37.0, -114.2], location_str="Southern California")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.0, -119.0, 37.0, -114.2], location_str="Southern California")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[34.4, -112.5, 37.5, -107.0], location_str="Four Corners")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[34.4, -112.5, 37.5, -107.0], location_str="Four Corners")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[37.0, -106.5, 38.5, -105.3], location_str="San Luis Valley")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[37.0, -106.5, 38.5, -105.3], location_str="San Luis Valley")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[31.3, -107.6, 31.8, -107.1], location_str="N Mexico 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[31.3, -107.6, 31.8, -107.1], location_str="N Mexico 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[39.6, -118.75, 40.1, -118.25], location_str="Carson Sink")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[39.6, -118.75, 40.1, -118.25], location_str="Carson Sink")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.9, -108.25, 31.4, -107.75], location_str="N Mexico 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.9, -108.25, 31.4, -107.75], location_str="N Mexico 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.6, -107.15, 31.1, -106.65], location_str="N Mexico 3")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.6, -107.15, 31.1, -106.65], location_str="N Mexico 3")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[40.65, -119.35, 41.15, -118.85], location_str="Black Rock 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[40.65, -119.35, 41.15, -118.85], location_str="Black Rock 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[32.45, -102.35, 32.95, -101.85], location_str="West Texas 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[32.45, -102.35, 32.95, -101.85], location_str="West Texas 1")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.15, -107.65, 30.65, -107.15], location_str="N Mexico 4")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.15, -107.65, 30.65, -107.15], location_str="N Mexico 4")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.5, -106.65, 31.0, -106.15], location_str="N Mexico 5")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.5, -106.65, 31.0, -106.15], location_str="N Mexico 5")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[32.65, -106.6, 33.15, -106.1], location_str="White Sands")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[32.65, -106.6, 33.15, -106.1], location_str="White Sands")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[33.0, -102.8, 33.5, -102.3], location_str="West Texas 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[33.0, -102.8, 33.5, -102.3], location_str="West Texas 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[37.55, -106.15, 38.05, -105.65], location_str="SLV2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[37.55, -106.15, 38.05, -105.65], location_str="SLV2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[29.05, -107.05, 29.55, -106.55], location_str="N Mexico 6")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[29.05, -107.05, 29.55, -106.55], location_str="N Mexico 6")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[35.2, -111.1, 35.7, -110.6], location_str="NE AZ")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[35.2, -111.1, 35.7, -110.6], location_str="NE AZ")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[35.65, -108.85, 36.15, -108.35], location_str="NW New Mexico")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[35.65, -108.85, 36.15, -108.35], location_str="NW New Mexico")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[40.25, -119.9, 40.75, -119.4], location_str="Black Rock 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[40.25, -119.9, 40.75, -119.4], location_str="Black Rock 2")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=True, boundary_box=[30.4, -108.15, 30.9, -107.65], location_str="N Mexico 7")
wldas.plot_wldas_plus_minus_30_average(plus_minus_30_dir, "WLDAS_plus_minus_30_plots_average", is_std=False, boundary_box=[30.4, -108.15, 30.9, -107.65], location_str="N Mexico 7")