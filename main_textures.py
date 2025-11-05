from USDA_texture_data import usda_texture_utils as usda
from GLDAS_soil_texture import gldas_texture_utils as gldas

# usda_filepath = "USDA_texture_data/USDA_texture_for_each_dust_event.csv"
# counts = usda.counts_of_usda_texture_values(usda_filepath)
# print(counts)

gldas_path = "GLDAS_soil_texture/GLDASp4_soilfraction_025d.nc4"
ds = gldas.open_gldas_file(gldas_path)
ds = gldas.filter_to_region(ds, location_name="Chihuahua")
clay_silt_sand = gldas.get_texture_averages_for_region(ds)
gldas.create_ternary_plot(clay_silt_sand, fig_dir="GLDAS_soil_texture", fig_name="ternary_chihuahua")

