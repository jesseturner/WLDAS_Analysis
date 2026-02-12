from modules_line_dust import line_dust_utils as dust
from modules_soil_orders import soil_orders_utils as orders

import pandas as pd

print("Opening dust dataset...")
location_name = "American Southwest"
dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
dust_df = dust.read_dust_data_into_df(dust_path)
dust_df = dust.filter_to_region(dust_df, location_name=location_name)
dust_df["datetime"] = pd.to_datetime(
    dust_df["Date (YYYYMMDD)"],
    format="%Y%m%d"
)

print("Opening soil orders dataset...")
usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
location_name="American Southwest"

min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)

soil_da = (
    rxr.open_rasterio(usda_filepath)
    .squeeze("band", drop=True)
    .rio.clip_box(
        minx=min_lon,
        miny=min_lat,
        maxx=max_lon,
        maxy=max_lat,
    )
)