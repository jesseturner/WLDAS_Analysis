import xarray as xr

def load_mf_data_with_xarray(file_list):
    '''
    Loads WLDAS data into an xarray dataset. 

    :param file_list: [str]
    '''

    ds = xr.open_mfdataset(file_list, combine='nested', concat_dim='time')
    ds = ds.drop_vars('time_bnds')
    ds.attrs.clear()
    ds = ds.sortby('time')

    return ds

def filter_by_bounds(ds, location_name="American Southwest"):
    '''
    Filters WLDAS xarray dataset to a specific region.
    
    :param ds: from load_data_with_xarray()
    :param location_name: str, options listed in _get_coords_for_region()
    '''

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    ds = ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max))
    return ds

def _get_coords_for_region(location_name):
    '''
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    '''
    locations = {
        "American Southwest": [(44, -128), (27.5, -100)],

        "Chihuahua": [(33.3, -110.0), (28.0, -105.3)],
        "West Texas": [(35.0, -104.0), (31.8, -100.5)],
        "Central High Plains": [(43.0, -105.0), (36.5, -98.0)],
        "Nevada": [(43.0, -120.7), (37.0, -114.5)],
        "Utah": [(42.0, -114.5), (37.5, -109.0)],
        "Southern California": [(37.0, -119.0), (30.0, -114.2)],
        "Four Corners": [(37.5, -112.5), (34.4, -107.0)],
        "San Luis Valley": [(38.5, -106.5), (37.0, -105.3)],

        "N Mexico 1": [(31.8, -107.6), (31.3, -107.1)],
        "Carson Sink": [(40.1, -118.75), (39.6, -118.25)],
        "N Mexico 2": [(31.4, -108.25), (30.9, -107.75)],
        "N Mexico 3": [(31.1, -107.15), (30.6, -106.65)],
        "Black Rock 1": [(41.15, -119.35), (40.65, -118.85)],
        "West Texas 1": [(32.95, -102.35), (32.45, -101.85)],
        "N Mexico 4": [(30.65, -107.65), (30.15, -107.15)],
        "N Mexico 5": [(31.0, -106.65), (30.5, -106.15)],
        "White Sands": [(33.15, -106.6), (32.65, -106.1)],
        "West Texas 2": [(33.5, -102.8), (33.0, -102.30)],
        "SLV2": [(38.05, -106.15), (37.55, -105.65)],
        "N Mexico 6": [(29.55, -107.05), (29.05, -106.55)],
        "NE AZ": [(35.7, -111.1), (35.2, -110.6)],
        "NW New Mexico": [(36.15, -108.85), (35.65, -108.35)],
        "Black Rock 2": [(40.75, -119.9), (40.25, -119.4)],
        "N Mexico 7": [(30.9, -108.15), (30.4, -107.65)],
    }
    coords = locations[location_name]
    lats = [p[0] for p in coords]
    lons = [p[1] for p in coords]

    lat_min, lat_max = min(lats), max(lats)
    lon_min, lon_max = min(lons), max(lons)

    return lat_min, lat_max, lon_min, lon_max

def filter_by_ever_dust_points(ds, dust_df):
    """
    Returns a moisture dataset with values within 
    a range of any point that has ever been a dust source.
    """

    #--- Set range from each dust source
    buffer_deg = 0.1

    #--- Initialize empty mask
    lat = ds['lat']
    lon = ds['lon']
    mask = xr.zeros_like(lat * 0 + lon * 0, dtype=bool)

    #--- Create mask with boxes around each dust point
    for point_lat, point_lon in zip(dust_df['latitude'], dust_df['longitude']):
        lat_mask = (lat >= point_lat - buffer_deg) & (lat <= point_lat + buffer_deg)
        lon_mask = (lon >= point_lon - buffer_deg) & (lon <= point_lon + buffer_deg)
        # Use broadcasting to apply lat/lon condition over grid
        point_mask = lat_mask & lon_mask
        mask = mask | point_mask
    
    #--- Apply mask to WLDAS dataset
    ds = ds.where(mask, drop=True)
    
    return ds

def filter_by_current_dust_points(ds, dust_df):
    """
    Returns a moisture dataset with values within 
    a range of any point that dust blew from on that day.
    """

    #--- Set range from each dust source
    buffer_deg = 0.1

    #--- Initialize empty mask
    lat = ds['lat']
    lon = ds['lon']
    mask = xr.zeros_like(lat * 0 + lon * 0, dtype=bool)

    #--- Get current day from ds
    #------ Assumes ds has a 'day' coordinate or variable
    current_day = ds['day'].values

    #--- Filter dust_df for current day
    dust_today = dust_df[dust_df['day'] == current_day]

    #--- Create mask with boxes around each dust point
    for point_lat, point_lon in zip(dust_today['latitude'], dust_today['longitude']):
        lat_mask = (lat >= point_lat - buffer_deg) & (lat <= point_lat + buffer_deg)
        lon_mask = (lon >= point_lon - buffer_deg) & (lon <= point_lon + buffer_deg)
        point_mask = lat_mask & lon_mask
        mask = mask | point_mask
    
    #--- Apply mask to WLDAS dataset
    ds_filtered = ds.where(mask, drop=True)
    
    return ds
