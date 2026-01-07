import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as feature
import numpy as np


def _plot_save(fig, fig_dir, fig_name):
    os.makedirs(f"{fig_dir}", exist_ok=True)
    plt.savefig(f"{os.path.join(fig_dir, fig_name)}.png", dpi=200, bbox_inches='tight')
    plt.close(fig)

    return

def plot_map_avg_moisture(ds, fig_title, location, fig_dir, fig_name):
    '''
    Creates an averaged map of soil moistures. 

    :param ds: WLDAS xarray dataset from utils_processing
    :param fig_dir: Where to save figure
    :param fig_name: Name of figure
    '''

    ds_mean = ds.mean(dim='time')

    projection=ccrs.PlateCarree(central_longitude=0)
    fig,ax=plt.subplots(1, figsize=(12,12),subplot_kw={'projection': projection})

    levels = np.linspace(0, 0.5, 25)
    c=ax.contourf(ds_mean.lon, ds_mean.lat, ds_mean['SoilMoi00_10cm_tavg'], cmap='coolwarm_r', extend='both', levels=levels)

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location)
    extent = [lon_min, lon_max, lat_min, lat_max]
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    clb = plt.colorbar(c, shrink=0.4, pad=0.02, ax=ax)
    clb.ax.tick_params(labelsize=15)
    clb.set_label("$m^3 m^{-3}$", fontsize=15)

    custom_ticks = [0, 0.1, 0.2, 0.3, 0.4, 0.5]
    clb.set_ticks(custom_ticks)

    ax.set_title(fig_title, fontsize=20, pad=10)
    ax.coastlines(resolution='50m', color='black', linewidth=1)
    ax.add_feature(feature.STATES, edgecolor='black', linewidth=1, zorder=6)

    _plot_save(fig, fig_dir, fig_name)
    return

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

def hist_comparison_plot(ds_all, ds_dust):
    '''
    Plot histograms of soil moisture comparison 
    between complete dataset and dust-filtered dataset.

    :param ds_all: from filter_by_bounds()
    :param ds_dust: from filter_by_dust_points()
    '''

    moist_all = ds_all["SoilMoi00_10cm_tavg"].values.flatten()
    moist_dust = ds_dust["SoilMoi00_10cm_tavg"].values.flatten()

    fig = plt.figure(figsize=(8,6))
    plt.hist(moist_all, bins=30, alpha=0.5, density=True, 
             label='All regions', color='blue')
    plt.hist(moist_dust, bins=30, alpha=0.5, density=True,
            label='Dust regions', color='orange')
    plt.xlabel('m$^3$ m$^{-3}$')
    plt.ylabel('Density')
    plt.title('Soil moisture content \n (0-10 cm below surface)')
    plt.legend()
    plt.show()
    
    _plot_save(fig, "figures", "example_hist")

    return

def hist_comparison_stats(ds_all, ds_dust):
    '''
    KS test and p-value for the dust and all soil moisture datasets. 
    
    :param ds_all: from filter_by_bounds()
    :param ds_dust: from filter_by_dust_points()
    '''

    from scipy.stats import ks_2samp

    moist_all = ds_all["SoilMoi00_10cm_tavg"].values.flatten()
    moist_dust = ds_dust["SoilMoi00_10cm_tavg"].values.flatten()
    
    moist_all = moist_all[~np.isnan(moist_all)]
    moist_dust = moist_dust[~np.isnan(moist_dust)]
    stat, p_value = ks_2samp(moist_all, moist_dust)
    print(f"KS statistic: {stat:.4f}, p-value: {p_value:.4f}")

    return

