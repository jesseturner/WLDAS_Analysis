from pathlib import Path
import requests, os, sys, pickle, json, re, glob
from tqdm import tqdm
import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from Line_dust_utils import line_dust_utils as dust
from datetime import datetime, timedelta

def get_wldas_data(date, chunks=None, print_vars=False, print_ds=False):
    download_dir = Path("WLDAS_data")
    filepath = _get_local_wldas(date, download_dir)
    if not filepath:
        filepath = _run_download_wldas(date, download_dir)
    if filepath:
        ds = load_data_with_xarray(filepath, chunks, print_vars, print_ds)
    else: 
        print("No data found locally or at download link.")
    
    return ds

def get_wldas_data_bulk_subset():
    print("Instructions: This is done through NASA DISC.")
    print("1. https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS")
    print("2. Subset directory")
    print("3. Download list of links")
    print("4. Earthdata authentication:")
    print("     .netrc with username and password")
    print("     .urs_cookies created")
    print("     .dodsrc with path to cookies and netrc")
    print("5. Add subset text file to directory <url.txt>")
    print("6. wget --load-cookies ~/.urs_cookies --save-cookies ~/.urs_cookies --keep-session-cookies --content-disposition -i '<url.txt>'")
    return

def _get_local_wldas(date, download_dir):
    date_str = date.strftime("%Y%m%d")
    matches = list(download_dir.glob(f"*{date_str}*"))
    if matches:
        filepath = str(matches[0])
        print(f"Found file: {filepath}")
    else: filepath = None
    return filepath

def _run_download_wldas(date, download_dir):
    #--- Set .netrc with GES DISC username and password
    #--- Add a reminder if there is a "no permissions" error

    YYYY = date.strftime('%Y')
    MM = date.strftime('%m')
    DD = date.strftime('%d')

    url = f"https://hydro1.gesdisc.eosdis.nasa.gov/data/WLDAS/WLDAS_NOAHMP001_DA1.D1.0/{YYYY}/{MM}/WLDAS_NOAHMP001_DA1_{YYYY}{MM}{DD}.D10.nc"

    #--- Create session with NASA Earthdata login
    session = requests.Session()
    session.auth = (os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD"))

    #--- Make download directory
    download_dir.mkdir(parents=True, exist_ok=True)

    filepath = _download_wldas(session, url, download_dir)
    return filepath

def _download_wldas(session, url, download_dir):
    print(f"Connecting to {url}...")
    response = session.get(url, stream=True)
    print("Connection established. Starting download...")

    if response.status_code == 200:

        filename = _extract_filename(response, url)
        filepath = download_dir / filename
        _write_file_to_local_disk(response, filepath, filename)

        print(f"Downloaded to {filepath}")
    else:
        print(f"Failed to download: {response.status_code} {response.reason}")
        print(response.text)

    return filepath

def _extract_filename(response, url):
    cd = response.headers.get('content-disposition')
    if cd and 'filename=' in cd:
        filename = cd.split('filename=')[-1].strip('\"')
    else:
        filename = url.split('/')[-1]
    return filename
    
def _write_file_to_local_disk(response, filepath, filename):
    total_size = int(response.headers.get('content-length', 0))
    chunk_size = 8192

    use_tqdm = sys.stderr.isatty() # Only use progress bar for in commandline
    with open(filepath, 'wb') as f, tqdm(
        total=total_size, unit='B', unit_scale=True, desc=filename, disable=not use_tqdm
    ) as pbar:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
    return

def load_data_with_xarray(filepath, chunks, print_vars, print_ds):
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

def filter_by_bounds(ds, bounds=None):
    if not isinstance(bounds, list) or len(bounds) != 4:
        print("Bounds must be a list of four coordinates: [Latitude South, Latitude North, Longitude West, Longitude East]")
        return
    ds = ds.sel(
        lat=slice(bounds[0], bounds[1]),
        lon=slice(bounds[2], bounds[3]))
    return ds

def filter_by_dust_points(ds, dust_path):
    #--- WLDAS dataset within a range of any point that has ever been a dust source

    dust_df = dust._read_dust_data_into_df(dust_path)

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

def _plot_save(fig, plot_dir, plot_path):
    plt.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(plot_path)
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

def _datetime_from_xarray_date(xarray_time):
    #--- grabbing the first time
    dt = xarray_time.values[0].astype('datetime64[ms]').astype('O')
    return dt

def get_wldas_plus_minus_30(dust_path, wldas_path, plus_minus_30_dir):
#--- For each dust case, get the WLDAS soil moisture for that location
#--- over the timespan from 30 days before to 30 days after
    wldas_path = Path(wldas_path)
    dust_df = dust._read_dust_data_into_df(dust_path)
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

def get_wldas_plus_minus_30_average_soil_texture(json_dir, usda_filepath, soil_id, soil_name):

    file_list_all = glob.glob(f"{json_dir}/*.json")

    file_list = _get_file_list_filtered_by_soil_texture(file_list_all, usda_filepath, soil_id)
    print(f"{len(file_list)} of {len(file_list_all)} found for {soil_name}.")

    average_list, std_list = _average_json_files(file_list)

    plus_minus_30_dir = "WLDAS_plus_minus_30_average_soil_textures"
    soil_name_save = soil_name.lower().replace(" ", "_")
    average_list_name = f"average_{soil_name_save}"
    std_list_name = f"std_{soil_name_save}"
    _save_plus_minus_30_list(plus_minus_30_dir, average_list, average_list_name)
    _save_plus_minus_30_list(plus_minus_30_dir, std_list, std_list_name)

    return

def _get_file_list_filtered_by_soil_texture(file_list, usda_filepath, soil_id):
    filtered_file_list = []
    texture_df = _open_usda_texture_csv(usda_filepath)
    count = 0

    for f in file_list:
        lat, lon = _parse_lat_lon(f)
        date = _parse_date(f)

        texture_case = texture_df[
                 (texture_df["lat"].astype(str) == str(lat)) & 
                 (texture_df["lon"].astype(str) == str(lon)) & 
                 (texture_df["YYYYMMDD"].astype(str) == str(date))]
        
        if len(texture_case) == 0:
            count += 1
            continue
        
        if texture_case.SAMPLE_1.values[0] == soil_id:
            filtered_file_list.append(f)
    print(f"{count} files not found.")

    return filtered_file_list


def _open_usda_texture_csv(usda_filepath):
    df = pd.read_csv(usda_filepath)
    return df

def counts_of_usda_texture_values(usda_filepath):
    df = _open_usda_texture_csv(usda_filepath)
    counts = df["SAMPLE_1"].value_counts().sort_index().to_dict()

    soil_mapping = {
        1: "Clay",
        2: "Clay loam",
        3: "Loam",
        4: "Loamy sand",
        5: "Sand",
        6: "Sandy clay",
        7: "Sandy clay loam",
        8: "Sandy loam",
        9: "Silt",
        10: "Silty clay",
        11: "Silty clay loam",
        12: "Silt loam"
    }

    counts_named = {soil_mapping[k].lower().replace(" ", "_"): v for k, v in counts.items()}

    return counts_named