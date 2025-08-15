import pandas as pd

def _read_dust_data_into_df(dust_path):
    
    dust_df = pd.read_csv(dust_path, sep=r'\s+', skiprows=2, header=None)
    dust_df.columns = ['Date (YYYYMMDD)', 'start time (UTC)', 'latitude', 'longitude', 'Jesse Check']

    #--- Clean lat/lon data
    dust_df['latitude'] = pd.to_numeric(dust_df['latitude'], errors='coerce')
    dust_df['longitude'] = pd.to_numeric(dust_df['longitude'], errors='coerce')
    dust_df = dust_df.dropna(subset=['latitude', 'longitude'])

    return dust_df