from modules_soil_orders import soil_orders_utils as soil_orders
from modules_line_dust import line_dust_utils as dust
import os

#--- Open soil orders file as GeoDataframe
# data_dir = "data/raw/wrb_soil_orders"
# wrb2014_file_dir = os.path.join(data_dir, "WRB2014_soil_map")
# gdf = soil_orders.open_wrb2014_file(wrb2014_file_dir)

#--- Get Line dust dataset
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

#--- Create dataframe of soil order for each event
# dust_gdf = soil_orders.convert_df_to_gdf(dust_df)
# dust_soil_df = soil_orders.get_soil_order_for_dust_events(gdf, dust_gdf)
# print(dust_soil_df)

#--- Count soil orders for each dust event
# counts_df = soil_orders.count_points_in_regions(gdf, dust_gdf)
# counts_df = soil_orders.add_info_to_counts(counts_df)

# plot_dir = "figures"
# print(counts_df)
# soil_orders.plot_counts(counts_df, plot_dir="figures", plot_name="wrb2014_counts")

#--- Count total soil order distributions
# counts_df_total = soil_orders.get_wrb2014_distributions(gdf)
# counts_df_total = soil_orders.add_info_to_counts(counts_df_total)
# soil_orders.plot_counts_and_total(counts_df, counts_df_total, plot_dir, "soil_orders/wrb2014_counts_and_total")

#--- Create table with legend
# soil_orders.create_legend_png(counts_df_total, plot_dir, "soil_orders/wrb2014_counts_legend")

#--- Plot map of soil order
# soil_orders.plot_map_for_sel_order(gdf, order_symbol_list=["CL", "RG", "FL"], 
#                                    location="American Southwest",
#                                    dust_df=dust_df,
#                                    plot_title="Map of Calcisols", 
#                                    plot_dir="figures", plot_name="map_calcisols")

#--- Open soil types USDA file
usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
soil_orders.usda_soil_types_figure(usda_filepath, dust_df, location_name="American Southwest")