from modules_line_dust import line_dust_utils as dust
from modules_texture import gldas_texture_utils as gldas
from modules_soil_orders import soil_orders_utils as soil_orders
import pandas as pd
import os

#--- Get dust data
dust_path="data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)

#--- Create universal table for all surface variables
uni_df = dust_df[['Date (YYYYMMDD)', 'latitude', 'longitude']].copy()
uni_df.columns = ['Date', 'Lat', 'Lon']

#--- Add texture data to universal table
gldas_path = "data/raw/gldas_soil_texture/GLDASp4_soilfraction_025d.nc4"
location_name = "American Southwest"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
texture_fractions_df = gldas.get_texture_for_dust_events(texture_ds, dust_df)
uni_df = pd.concat([uni_df.reset_index(drop=True), texture_fractions_df.reset_index(drop=True)], axis=1)
uni_df = uni_df.rename(columns={'Clay': 'GLDAS (Clay)', 
                                'Sand': 'GLDAS (Sand)',
                                'Silt': 'GLDAS (Silt)',})

#--- Add soil orders data to universal table
#------ This needs to be one-hot encoded (scikit-learn has a function to do this)
dust_gdf = soil_orders.convert_df_to_gdf(dust_df)
wrb_path = "data/raw/wrb_soil_orders/WRB2014_soil_map"
gdf = soil_orders.open_wrb2014_file(wrb_path)
dust_soil_df = soil_orders.get_soil_order_for_dust_events(gdf, dust_gdf)
column = ["SU_SYMBOL"]
uni_df = pd.concat([uni_df.reset_index(drop=True), dust_soil_df[column].reset_index(drop=True)], axis=1)
uni_df = uni_df.rename(columns={'SU_SYMBOL': 'Soil Order'})
print(uni_df)

#--- Fill dataframe with non-dust days and locations