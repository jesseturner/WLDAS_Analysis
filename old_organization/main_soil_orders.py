from soil_orders import soil_orders_utils as soil_orders
from Line_dust_data import line_dust_utils as dust
import os

#--- Open soil orders file as GeoDataframe
plot_dir = "/home/jturner/WLDAS_Analysis/soil_orders"
wrb2014_file_dir = os.path.join(plot_dir, "WRB2014_soil_map")
gdf = soil_orders.open_wrb2014_file(wrb2014_file_dir)

#--- Get Line dust dataset
dust_path = "/home/jturner/WLDAS_Analysis/Line_dust_data/dust_dataset_final_20241226.txt"
df = dust.read_dust_data_into_df(dust_path)
dust_gdf = soil_orders.convert_df_to_gdf(df)

#--- Create dataframe of soil order for each event
dust_soil_df = soil_orders.get_soil_order_for_dust_events(gdf, dust_gdf)
print(dust_soil_df)

#--- Count soil orders for each dust event
counts_df = soil_orders.count_points_in_regions(gdf, dust_gdf)
counts_df = soil_orders.add_info_to_counts(counts_df)
# print(counts_df)
# soil_orders.plot_counts(counts_df, plot_dir, "soil_orders/wrb2014_counts")

#--- Count total soil order distributions
# counts_df_total = soil_orders.get_wrb2014_distributions(gdf)
# counts_df_total = soil_orders.add_info_to_counts(counts_df_total)
# soil_orders.plot_counts_and_total(counts_df, counts_df_total, plot_dir, "soil_orders/wrb2014_counts_and_total")

#--- Create table with legend
# soil_orders.create_legend_png(counts_df_total, plot_dir, "soil_orders/wrb2014_counts_legend")