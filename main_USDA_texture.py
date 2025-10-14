from USDA_texture_data import usda_texture_utils as texture

usda_filepath = "USDA_texture_data/USDA_texture_for_each_dust_event.csv"

counts = texture.counts_of_usda_texture_values(usda_filepath)
print(counts)
