import xarray as xr
import matplotlib.pyplot as plt
import os
import pandas as pd
import plotly.express as px

def open_gldas_file(gldas_path):
    ds = xr.open_dataset(gldas_path)
    return ds

def filter_to_region(ds, location_name):

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    filtered_ds = ds.sel(
        lat=slice(lat_min, lat_max),
        lon=slice(lon_min, lon_max)
    )
    return filtered_ds

def _get_coords_for_region(location_name):
    """
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    """
    locations = {
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

def get_texture_averages_for_region(ds):
    clay_fraction = ds["GLDAS_soilfraction_clay"].mean(dim=['lat', 'lon', 'time'])
    sand_fraction = ds["GLDAS_soilfraction_sand"].mean(dim=['lat', 'lon', 'time'])
    silt_fraction = ds["GLDAS_soilfraction_silt"].mean(dim=['lat', 'lon', 'time'])
    texture_fractions_df = pd.DataFrame([{
        'Clay': clay_fraction.values, 
        'Sand': sand_fraction.values,
        'Silt': silt_fraction.values}])

    return texture_fractions_df

def create_ternary_plot(texture_fractions_df, fig_dir, fig_name, location_name):
    """
    clay_silt_sand : [clay_fraction, silt_fraction, sand_fraction], like from get_texture_averages_for_region()
    """
    fig = px.scatter_ternary(texture_fractions_df, a="Sand", b="Silt", c="Clay", 
                             title=f"Distribution of Soil Texture: {location_name}")
    
    fig.update_traces(marker=dict(
        size=15,
        color='royalblue',
        line=dict(width=1, color='black'),
        opacity=0.8
    ))
    
    fig.update_layout(
        ternary=dict(
            aaxis=dict(showticklabels=False),
            baxis=dict(showticklabels=False),
            caxis=dict(showticklabels=False)
        ),
    )

    fig.write_image(f"{os.path.join(fig_dir, fig_name)}.png", width=600, height=600, scale=2) 

    return

def _plot_save(fig, fig_dir, fig_name):
    os.makedirs(f"{fig_dir}", exist_ok=True)
    plt.savefig(f"{os.path.join(fig_dir, fig_name)}.png", dpi=200, bbox_inches='tight')
    plt.close(fig)

    return
