import os, pickle, json, re, glob
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from datetime import datetime, timedelta
import pandas as pd

def load_data_with_xarray(filepath, chunks=None, print_vars=False, print_ds=False):
    '''
    Loads WLDAS data into an xarray dataset. 

    :param filepath: str
    :param chunks: int
    :param print_vars: bool
    :param print_ds: bool
    '''
    ds = None

    if filepath:
        try:
            ds = xr.open_dataset(filepath, chunks=chunks)
            if print_ds: print(ds)
            if print_vars: 
                for var in ds.data_vars:
                    print(f"{var} => {ds[var].attrs.get("standard_name")}, {ds[var].attrs.get("long_name")}, units = {ds[var].attrs.get("units")}")
        except (FileNotFoundError, OSError) as e:
            print(f"Could not open dataset at {filepath}: {e}")
            ds = None
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

def filter_by_dust_points(ds, dust_df):
    """
    WLDAS dataset within a range of any point that has ever been a dust source.
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

def create_hist_for_variables(ds, hist_dir):
    hist_store = {}  # Will hold {"variable_name": (counts, bin_edges)}

    for variable in ds.data_vars:
        data = ds[variable].values.flatten()
        data = data[np.isfinite(data)]

        # Skip non-numeric data types (e.g., datetime64, object)
        if not np.issubdtype(data.dtype, np.number):
            print(f"Skipping variable '{variable}' of type {data.dtype}")
            continue

        date = _datetime_from_xarray_date(ds.time)
        long_name = ds[variable].attrs.get("long_name")
        units = ds[variable].attrs.get("units")
        bin_edges = np.linspace(np.nanmin(data), np.nanmax(data), num=51)
        counts, _ = np.histogram(data, bins=bin_edges)
        hist_store[variable] = (long_name, units, counts, bin_edges)

        os.makedirs(hist_dir, exist_ok=True)
        with open(f"{hist_dir}/{date.strftime('%Y%m%d')}.pkl", "wb") as f:
            pickle.dump(hist_store, f)

    return ds

def _plot_save(fig, fig_dir, fig_name):
    os.makedirs(f"{fig_dir}", exist_ok=True)
    plt.savefig(f"{os.path.join(fig_dir, fig_name)}.png", dpi=200, bbox_inches='tight')
    plt.close(fig)

    return

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

def _datetime_from_xarray_date(xarray_time):
    #--- grabbing the first time
    dt = xarray_time.values[0].astype('datetime64[ms]').astype('O')
    return dt

def get_wldas_plus_minus_30(dust_df, wldas_path, plus_minus_30_dir):
#--- For each dust case, get the WLDAS soil moisture for that location
#--- over the timespan from 30 days before to 30 days after
    wldas_path = wldas_path
    for index, row in dust_df.iterrows():
        print(f"Plus minus 30 for {index} of {len(dust_df)}")
        date = str(row['Date (YYYYMMDD)'])
        time = str(int(row['start time (UTC)']))
        lat = str(row['latitude'])
        lon = str(row['longitude'])

        plus_minus_30_list = _loop_through_plus_minus_30(date, wldas_path, lat, lon)

        lat_clean = lat.replace(".", "")
        lon_clean = lon.replace("-", "").replace(".", "")
        list_name = f"{date}_{time}_lat{lat_clean}_lon{lon_clean}"
        _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, list_name)
    return


def _loop_through_plus_minus_30(date, wldas_path, lat, lon):
    base_date = datetime.strptime(date, "%Y%m%d")
    plus_minus_30_list = []
    for offset in range(-30, 31):
        date_i = base_date + timedelta(days=offset)
        date_i_str = datetime.strftime(date_i, "%Y%m%d")
        wldas_filepath = wldas_path / f"WLDAS_NOAHMP001_DA1_{date_i_str}.D10.nc.SUB.nc4"
        ds = load_data_with_xarray(wldas_filepath, chunks=None, print_vars=False, print_ds=False)
        if ds: 
            ds_point_value = _filter_wldas_by_lat_lon(ds, lat, lon)
            if ds_point_value:
                plus_minus_30_list.append(ds_point_value)
            else: 
                plus_minus_30_list.append(np.nan)
        else: 
            plus_minus_30_list.append(np.nan)

    return plus_minus_30_list

def _filter_wldas_by_lat_lon(ds, lat, lon):
    ds_point = ds.sel(lat=lat, lon=lon, method="nearest")
    ds_point_soil_moisture = float(ds_point['SoilMoi00_10cm_tavg'].values[0])
    return ds_point_soil_moisture

def _save_plus_minus_30_list(plus_minus_30_dir, plus_minus_30_list, list_name):
    os.makedirs(plus_minus_30_dir, exist_ok=True)

    if isinstance(plus_minus_30_list, np.ndarray):
        plus_minus_30_list = plus_minus_30_list.tolist()

    with open(f"{plus_minus_30_dir}/{list_name}.json", "w") as f:
        json.dump(plus_minus_30_list, f)
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

def get_wldas_plus_minus_30_average(json_dir, boundary_box=[], location_str="American Southwest"):
    """
    boundary_box: [lat_min, lon_min, lat_max, lon_max]
    """

    file_list = glob.glob(f"{json_dir}/*.json")

    if boundary_box:
        file_list = _get_file_list_filtered_by_lat_lon(file_list, boundary_box)

    average_list, std_list = _average_json_files(file_list)

    plus_minus_30_dir = "WLDAS_plus_minus_30_average"
    location_str_save = location_str.lower().replace(" ", "_")
    average_list_name = f"average_{location_str_save}"
    std_list_name = f"std_{location_str_save}"
    _save_plus_minus_30_list(plus_minus_30_dir, average_list, average_list_name)
    _save_plus_minus_30_list(plus_minus_30_dir, std_list, std_list_name)

    return

def plot_wldas_plus_minus_30_average(json_filepath_average,  plot_dir, location_str="American Southwest"):
    with open(json_filepath_average, "r") as f:
        plus_minus_30_list = json.load(f)

    plot_title = f"Average soil moisture associated with each blowing dust event \n ({location_str})"
    location_str_save = location_str.lower().replace(" ", "_")
    plot_path = f"{plot_dir}/average_soil_moisture_{location_str_save}.png"
        
    _line_plot(plus_minus_30_list, plot_title, plot_dir, plot_path)

    return

def _average_json_files(file_list):
    all_data = []
    for file_path in file_list:
        with open(file_path, 'r') as f:
            try: 
                data = json.load(f)
            except Exception as e:
                print(f"Could not open json at {f}: {e}")
            all_data.append(data)

    all_data_array = np.array(all_data)
    average_list = np.nanmean(all_data_array, axis=0)
    std_list = np.nanstd(all_data_array, axis=0)
    return average_list, std_list

def _get_file_list_filtered_by_lat_lon(file_list, boundary_box):
    filtered_file_list = []
    lat_min, lon_min, lat_max, lon_max = boundary_box

    for f in file_list:
        lat, lon = _parse_lat_lon(f)
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            filtered_file_list.append(f)

    return filtered_file_list
        

def _parse_lat_lon(filename: str) -> tuple[float, float]:
    """
    Extract latitude and longitude from filename.
    Example: '..._lat3062_lon10797.json' -> (30.62, -107.97)
    """
    match = re.search(r"lat(\d+)_lon(\d+)", filename)
    if not match:
        raise ValueError(f"Could not parse lat/lon from {filename}")
    
    lat_str, lon_str = match.groups()
    lat = float(lat_str[:2] + "." + lat_str[2:])
    lon = -float(lon_str[:3] + "." + lon_str[3:])  # negative for west
    return lat, lon

def _parse_date(filename):
    match = re.search(r"/(\d{8})_", filename)
    if match:
        date_str = match.group(1)
    return date_str

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

def create_region_average_over_time(wldas_dir, location_name, save_dir):
    """
    Get average soil moistures for a region over the times in the WLDAS directory.
    """

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location_name)

    dates = []
    moistures = []
    std = []
    file_list = glob.glob(os.path.join(wldas_dir, "*.nc4"))
    for count, filepath in enumerate(file_list, start=1):
        ds = load_data_with_xarray(os.path.join(wldas_dir,filepath))

        filtered_ds = ds.sel(
            lat=slice(lat_min, lat_max),
            lon=slice(lon_min, lon_max)
        )

        dt = filtered_ds.time
        moisture = filtered_ds["SoilMoi00_10cm_tavg"].mean(dim=['time', 'lat', 'lon'])
        moisture_std = filtered_ds["SoilMoi00_10cm_tavg"].std(dim=['time', 'lat', 'lon'])
        dates.append(dt[0].values)
        moistures.append(moisture.values)
        std.append(moisture_std.values)

        if count % 100 == 0:
            print(f"{count} / {len(file_list)}")

    region_moisture_df = pd.DataFrame({
        'moisture': moistures, 
        'standard deviation': std}, 
        index=dates
    )
    region_moisture_df.sort_index(inplace=True)

    region_moisture_df.to_csv(os.path.join(save_dir,f'region_moisture_{location_name}.csv'))

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