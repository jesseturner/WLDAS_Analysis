from soil_orders import soil_orders_utils as soil_orders
from Line_dust_data import line_dust_utils as dust
import os

plot_dir = "/home/jturner/WLDAS_Analysis/soil_orders"
wrb2014_file_dir = os.path.join(plot_dir, "WRB2014_soil_map")
gdf = soil_orders.open_wrb2014_file(wrb2014_file_dir, plot_dir, os.path.join(plot_dir, "example_wrb2014_plot"))

dust_path = "/home/jturner/WLDAS_Analysis/Line_dust_data/dust_dataset_final_20241226.txt"
df = dust.read_dust_data_into_df(dust_path)
dust_gdf = dust.convert_df_to_gdf(df)

counts_df = soil_orders.count_points_in_regions(gdf, dust_gdf)
counts_df = soil_orders.add_info_to_counts(counts_df)
print(counts_df)

soil_orders.plot_counts(counts_df, plot_dir, "soil_orders/wrb2014_counts")
soil_orders.create_legend_png(counts_df, plot_dir, "soil_orders/wrb2014_counts_legend")