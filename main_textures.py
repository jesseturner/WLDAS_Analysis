from modules_texture import gldas_texture_utils as gldas
from modules_line_dust import line_dust_utils as dust

#--- Open GLDAS soil textures (percentages)
gldas_path = "data/raw/gldas_soil_texture/GLDASp4_soilfraction_025d.nc4"
location_name = "American Southwest"
texture_ds = gldas.open_gldas_file(gldas_path)
texture_ds = gldas.filter_to_region(texture_ds, location_name)
# print(texture_ds)
texture_average_df = gldas.get_texture_averages_for_region(texture_ds)
# print(texture_average_df)

#--- Plot soil texture for each dust event
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_region_df = dust.filter_to_region(dust_df, location_name=location_name)
texture_fractions_df = gldas.get_texture_for_dust_events(texture_ds, dust_df)
print(texture_fractions_df)

gldas.create_ternary_plot(texture_fractions_df, fig_dir="figures", 
    fig_name=f"ternary_{location_name.lower().replace(" ", "_")}_dust_producing", 
    fig_title=f"Distribution of dust-producing points: {location_name}")

#--- Plot soil texture for full region
texture_fractions_df = gldas.get_texture_all(texture_ds)

gldas.create_ternary_plot(texture_fractions_df, fig_dir="figures", 
    fig_name=f"ternary_{location_name.lower().replace(" ", "_")}_all", 
    fig_title=f"Distribution of all points: {location_name}")