import soil_orders_utils as soil_orders
import os

plot_dir = "/home/jturner/WLDAS_Analysis/soil_orders"
wrb2014_file_dir = os.path.join(plot_dir, "WRB2014_soil_map")
soil_orders.open_wrb2014_file(wrb2014_file_dir, plot_dir, os.path.join(plot_dir, "example_wrb2014_plot"))
