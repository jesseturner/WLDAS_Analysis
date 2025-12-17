import os
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as feature
import numpy as np
#=========
import matplotlib.cm as cm
import pickle, json, re
import pandas as pd


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



#==========================================
# Functions below are being improved
#==========================================

def _datetime_from_xarray_date(xarray_time):
    #--- grabbing the first time
    dt = xarray_time.values[0].astype('datetime64[ms]').astype('O')
    return dt

def plot_hist_for_variables(ds, hist_dir):
    date = _datetime_from_xarray_date(ds.time)
    
    with open(f"{hist_dir}/{date.strftime('%Y%m%d')}.pkl", "rb") as f:
        hist_store = pickle.load(f)
    os.makedirs(f"{hist_dir}", exist_ok=True)
    for variable in ds.data_vars:
        if variable not in hist_store:
            print(f"Skipping '{variable}' — no histogram stored.")
            continue

        long_name, units, counts, bin_edges = hist_store[variable]
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

        fig = plt.figure(figsize=(8, 4))
        plt.bar(bin_centers, counts, width=np.diff(bin_edges), align="center", edgecolor="blue", color='blue', alpha=0.7,)
        plt.title(f"Histogram of {variable} ({long_name})")
        plt.xlabel(f"{units}")
        plt.ylabel("Frequency")

        _plot_save(fig, hist_dir, f"{hist_dir}/{variable}.png")
    return

def plot_hist_for_moisture(hist_dir):
    with open(os.path.join(hist_dir,"dust_points_20010106.pkl"), "rb") as f:
        hist_store = pickle.load(f)

        moist_data = hist_store['SoilMoi00_10cm_tavg']
        bin_edges = moist_data[3]
        counts = moist_data[2]
        widths = bin_edges[1:] - bin_edges[:-1]

        fig = plt.figure(figsize=(8, 4))
        plt.bar(bin_edges[:-1], counts, width=widths, align="center", edgecolor="blue", color='blue', alpha=0.7,)
        plt.title(f"Histogram of soil moisture")
        plt.xlabel("$ m^{3} m^{-3} $")
        plt.ylabel("Frequency")

        _plot_save(fig, "figures", "example_hist")
    return

def plot_wldas_plus_minus_30(json_filepath, plot_dir):
    with open(json_filepath, "r") as f:
        plus_minus_30_list = json.load(f)

    date_str, time_str, lat_str, lon_str = _get_features_from_json_filename(json_filepath)
    formatted_coords = _get_formatted_coords(lat_str, lon_str)
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]} {time_str[:2]}:{time_str[2:]}"

    plot_title = f"{formatted_date} {formatted_coords}"
    plot_path = f"{plot_dir}/{date_str}_{time_str}_{lat_str}_{lon_str}.png"

    _line_plot(plus_minus_30_list, plot_title, plot_dir, plot_path)
    return

def _get_features_from_json_filename(json_filepath):
    m = re.search(r'(\d{8})_(\d{4})_lat(\d+)_lon(\d+)', json_filepath)
    if m:
        date_str, time_str, lat_str, lon_str = m.groups()
    return date_str, time_str, lat_str, lon_str

def _get_formatted_coords(lat_str, lon_str):
    lat = int(lat_str) / 100
    lon = -int(lon_str) / 100
    formatted_coords = f"({lat:.2f}, {lon:.2f})"
    return formatted_coords

def _line_plot(data, plot_title, plot_dir, plot_path, ylim=None):
    """
    y_lim: [min, max]
    """

    fig = plt.figure(figsize=(8, 4))
    plt.plot(data, color='0', marker='o')
    plt.title(plot_title)
    plt.ylim(ylim)
    plt.xlabel("Days From Dust Event")
    plt.xticks(np.arange(0, 61, 3), labels=np.arange(-30, 31, 3))
    plt.ylabel("Soil Moisture (m$^3$/m$^3$)")

    _plot_save(fig, plot_dir, plot_path)
    return

def plot_wldas_plus_minus_30_average(json_filepath_average,  plot_dir, location_str="American Southwest"):
    with open(json_filepath_average, "r") as f:
        plus_minus_30_list = json.load(f)

    plot_title = f"Average soil moisture associated with each blowing dust event \n ({location_str})"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/average_soil_moisture_{location_str_save}.png"
        
    _line_plot(plus_minus_30_list, plot_title, plot_dir, plot_path)

    return

def plot_wldas_plus_minus_30_average_std(json_filepath_average, json_filepath_std, plot_dir, location_str="American Southwest"):
    with open(json_filepath_average, "r") as f:
        plus_minus_30_list = json.load(f)

    with open(json_filepath_std, "r") as f:
        plus_minus_30_list_std = json.load(f)

    plot_title = f"Average soil moisture associated with each blowing dust event \n ({location_str})"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/average_soil_moisture_{location_str_save}.png"
        
    _line_plot_dual(plus_minus_30_list, plus_minus_30_list_std, plot_title, plot_dir, plot_path)

    return

def _line_plot_dual(data1, data2, plot_title, plot_dir, plot_path, ylim=None):

    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax1.plot(data1, color='0', marker='o', label="Average Soil Moisture")
    ax1.set_xlabel("Days From Dust Event")
    ax1.set_xticks(np.arange(0, 61, 3))
    ax1.set_xticklabels(np.arange(-30, 31, 3))
    ax1.set_ylabel("Soil Moisture (m$^3$/m$^3$)")
    y_lim1, y_lim2 = _get_sliding_y_window(ax1, window_size=0.05)
    ax1.set_ylim(y_lim1, y_lim2)
    
    ax2 = ax1.twinx()
    ax2.plot(data2, color='Grey', marker='.', label="Standard Deviation", alpha=0.4)
    ax2.set_ylim(0.02, 0.08)
    ax2.set_ylabel("Standard Deviation")

    plt.title(plot_title)
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc="upper right")

    _plot_save(fig, plot_dir, plot_path)
    return

def _get_sliding_y_window(ax, window_size):
    ymin, ymax = ax.get_ylim()
    ycenter = (ymin + ymax) / 2
    y_lim1, y_lim2 = ycenter - window_size/2, ycenter + window_size/2

    return y_lim1, y_lim2

def plot_wldas_plus_minus_30_average_all(average_dir, std_dir=None, plot_dir="WLDAS_plus_minus_30_plots", counts_dict=None):
#--- This function is not refined
    fig, ax = plt.subplots(figsize=(9, 12))

    files = [f for f in os.listdir(average_dir) if f.endswith(".json")]
    hex_colors = [
        "#1f77b4",  # bright blue
        "#ff7f0e",  # orange
        "#2ca02c",  # green
        "#d62728",  # red
        "#9467bd",  # purple
        "#8c564b",  # brown
        "#e377c2"   # pink
    ]

    #--- Filter files to counts greater than 50
    if counts_dict:
        files = [f for f in files if counts_dict[f.replace("average_", "").replace(".json", "")] > 50]

    for i, fname in enumerate(files):
        if fname.endswith(".json"):
            fpath = os.path.join(average_dir, fname)
            with open(fpath, "r") as f:
                data = json.load(f)
            
            type_name = fname.replace("average_", "").replace(".json", "")
            label = f"{os.path.splitext(fname)[0].replace("_", " ").replace("average ", "")} ({counts_dict[type_name]} cases)"
            color = hex_colors[i % len(hex_colors)]
            width = 6*(counts_dict[type_name] - min(counts_dict.values())) / (max(counts_dict.values()) - min(counts_dict.values()))
            ax.plot(data, linestyle='-', color=color, label=label, linewidth=width)

            if std_dir:
                fname = fname.replace("average", "std")
                fpath = os.path.join(std_dir, fname)
                with open(fpath, "r") as f:
                    std = json.load(f)
                ax.fill_between(range(len(data)), 
                    np.array(data) - np.array(std)/15, np.array(data) + np.array(std)/15, color=color, alpha=0.1)

    ax.set_xticks(np.arange(0, 61, 3))
    ax.set_xticklabels(np.arange(-30, 31, 3))
    ax.axvline(x=30, color='grey', linestyle='-', linewidth=6, zorder=-1, alpha=0.1)
    plot_title = f"Average soil moisture associated with each blowing dust event"
    plot_path = f"{plot_dir}/average_soil_moisture_all.png"

    plt.title(plot_title)
    plt.xlabel("Days From Dust Event")
    plt.ylabel("Soil Moisture (m$^3$/m$^3$)")
    plt.legend()

    _plot_save(fig, plot_dir, plot_path)

    return

def plot_region_average_over_time(csv_path,  plot_dir, location_str):
    moisture_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    plot_title = f"Average soil moisture in {location_str}"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/region_moisture_{location_str_save}.png"

    fig, ax = plt.subplots(figsize=(24, 6))
    ax.plot(moisture_df['moisture'], linestyle='-', color='black')
    plt.title(plot_title)
    plt.xlabel("Date")
    plt.ylabel("Soil Moisture (m$^3$/m$^3$)")
    _plot_save(fig, plot_dir, plot_path)

    return

def plot_region_average_over_year(csv_path, dust_region_df, plot_dir, location_str):
    """
    Plotting the day-of-year moisture and dust events. 
    csv_path : created in create_region_average_over_time(). 
    dust_region_df : created in line_dust_utils, read_dust_data_into_df() and filter_to_region().
    """

    moisture_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)
    moisture_df['year'] = moisture_df.index.year
    moisture_df['doy'] = moisture_df.index.dayofyear

    dust_region_df = dust_region_df.copy()
    dust_region_df['date'] = pd.to_datetime(dust_region_df['Date (YYYYMMDD)'], format='%Y%m%d')
    dust_region_df['year'] = dust_region_df['date'].dt.year
    dust_region_df['doy'] = dust_region_df['date'].dt.dayofyear

    fig, ax = plt.subplots(figsize=(18, 6))

    years = sorted(moisture_df['year'].unique())
    colors = cm.copper(np.linspace(0, 1, len(years)))

    #--- Plotting soil moisture lines
    for color, (year, group) in zip(colors, moisture_df.groupby('year')):
        plt.plot(group['doy'], group['moisture'], color=color, label=str(year), zorder=2)

    #--- Plotting dust events
    for doy in sorted(dust_region_df['doy'].unique()):
        plt.axvline(doy, color='blue', linestyle='-', alpha=0.6, linewidth=1, zorder=1)

    plot_title = f"Average soil moisture in {location_str}"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/region_moisture_{location_str_save}_year.png"

    plt.title(plot_title)
    plt.xlabel("Day of Year")
    plt.ylabel("Soil Moisture (m$^3$/m$^3$)")
    plt.legend()
    _plot_save(fig, plot_dir, plot_path)

    return

def plot_frequency_analysis(csv_path, dust_region_df, plot_dir, location_str):

    moisture_df = pd.read_csv(csv_path, index_col=0, parse_dates=True)

    #--- Get dust events per day, filling in missing days with zeroes
    dust_region_df = dust_region_df.copy()
    dust_region_df['date'] = pd.to_datetime(dust_region_df['Date (YYYYMMDD)'], format='%Y%m%d')
    daily_counts = dust_region_df.groupby('date').size()
    all_days = pd.date_range(daily_counts.index.min(), daily_counts.index.max())
    daily_counts = daily_counts.reindex(all_days, fill_value=0)
    dust_values = daily_counts.values

    #--- Normalize data
    moist_values = moisture_df["moisture"] - np.mean(moisture_df["moisture"])
    dust_values = dust_values - np.mean(dust_values)

    #--- FFT magnitudes
    moist_fft_values = np.abs(np.fft.rfft(moist_values))
    dust_fft_values = np.abs(np.fft.rfft(dust_values))

    #--- Frequencies in cycles per year
    moist_freq = np.fft.rfftfreq(len(moist_values), d=1.0/365.25)
    dust_freq = np.fft.rfftfreq(len(dust_values), d=1.0/365.25)

    nyquist = moist_freq[-1]
    print("Nyquist frequency (cycles/year):", nyquist)

    fig, ax = plt.subplots(figsize=(18, 6))

    color1 = "#377eb8"
    ax.plot(moist_freq, moist_fft_values, color=color1, linewidth=3, alpha=0.6)
    ax.tick_params(axis='y', labelcolor=color1)
    ax.set_ylabel('Moisture Amplitudes', color=color1, size=24) 
    ax.set_xlim(0,6)
    ax.set_xlabel('Frequencies in cycles per year', color='black', size=24) 
    ax.tick_params(axis='x', labelsize=18)
    
    ax1 = ax.twinx()
    color2 = "#AB7A4A"
    ax1.plot(dust_freq, dust_fft_values, color=color2, linewidth=3, alpha=0.6)
    ax1.tick_params(axis='y', labelcolor=color2)
    ax1.set_ylabel('Dust Amplitudes', color=color2, size=24) 

    plot_title = f"Frequency Spectrum (FFT) of soil moisture in {location_str}"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/frequencies_{location_str_save}_year.png"

    plt.title(plot_title, size=24)
    plt.xlabel("Frequency (cycles per year)")
    _plot_save(fig, plot_dir, plot_path)


    return