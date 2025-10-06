import pandas as pd
from shapely.geometry import Point
import geopandas as gpd

def read_dust_data_into_df(dust_path):
    
    dust_df = pd.read_csv(dust_path, sep=r'\s+', skiprows=2, header=None)
    dust_df.columns = ['Date (YYYYMMDD)', 'start time (UTC)', 'latitude', 'longitude', 'Jesse Check']

    #--- Clean lat/lon data
    dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
    dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')
    dust_df = dust_df.dropna(subset=['latitude', 'longitude'])

    return dust_df

def convert_df_to_gdf(df):
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    #--- EPSG:4326 is the standard for lat/lon coordinates (WGS84)
    gdf_points = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    return gdf_points