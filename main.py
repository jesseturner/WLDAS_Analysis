from Line_dust_data import line_dust_utils as dust
from GLDAS_soil_texture import gldas_texture_utils as gldas
import pandas as pd

#--- Get dust data
dust_path="Line_dust_data/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_region_df = dust.filter_to_region(dust_df, location_name="Chihuahua")

#--- Create universal table for all surface variables
uni_df = dust_df[['Date (YYYYMMDD)', 'latitude', 'longitude']].copy()
uni_df.columns = ['Date', 'Lat', 'Lon']

#--- Add texture data to universal table
gldas_path = "GLDAS_soil_texture/GLDASp4_soilfraction_025d.nc4"
location_name = "American Southwest"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
texture_fractions_df = gldas.get_texture_for_dust_events(texture_ds, dust_df)
uni_df = pd.concat([uni_df.reset_index(drop=True), texture_fractions_df.reset_index(drop=True)], axis=1)
uni_df = uni_df.rename(columns={'Clay': 'GLDAS (Clay)', 
                                'Sand': 'GLDAS (Sand)',
                                'Silt': 'GLDAS (Silt)',})
print(uni_df)