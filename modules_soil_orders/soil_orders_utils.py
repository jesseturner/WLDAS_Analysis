import geopandas as gpd
import os, glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from shapely.geometry import Point
import geopandas as gpd
import cartopy.crs as ccrs
import cartopy.feature as cfeature

def open_wrb2014_file(wrb2014_file_dir):
    shapefiles = glob.glob(os.path.join(wrb2014_file_dir, "*.shp"))
    layers = [gpd.read_file(shp) for shp in shapefiles]
    print(f"Loaded {len(layers)} shapefiles")

    gdf = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True))
    #--- EPSG:4326 is the standard for lat/lon coordinates (WGS84)
    gdf = gdf.to_crs("EPSG:4326")
    return gdf

def count_points_in_regions(gdf_regions, gdf_points):
    points_with_regions = gpd.sjoin(gdf_points, gdf_regions, how="left", predicate="within")
    counts_df = points_with_regions.groupby('SU_SYMBOL').size().reset_index(name='count')
    
    return counts_df

def get_soil_order_for_dust_events(gdf_regions, gdf_points):
    gdf_points = gdf_points.to_crs(gdf_regions.crs)

    dust_soil_df = gpd.sjoin(
        gdf_points,
        gdf_regions[['SU_SYMBOL', 'geometry']],  # only keep needed columns
        how='left',
        predicate='within'  # or 'intersects' depending on your data
    )
    return dust_soil_df

def convert_df_to_gdf(df): 
    """
    Dust dataframe to format comparable to soil orders.
    """
    geometry = [Point(xy) for xy in zip(df['longitude'], df['latitude'])]
    #--- EPSG:4326 is the standard for lat/lon coordinates (WGS84)
    gdf_points = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    return gdf_points

def add_info_to_counts(df_counts):
    code_info = [
        {'SU_SYMBOL': 'HS', 'name': 'Histosols', 'description': '', 'category': 'Soils with thick organic layers'},
        
        {'SU_SYMBOL': 'AT', 'name': 'Anthrosols', 'description': 'With long and intensive agricultural use', 'category': 'Soils with strong human influence'},
        {'SU_SYMBOL': 'TC', 'name': 'Technosols', 'description': 'Containing significant amounts of artefacts', 'category': 'Soils with strong human influence'},
        
        {'SU_SYMBOL': 'CR', 'name': 'Cryosols', 'description': 'Permafrost-affected', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'LP', 'name': 'Leptosols', 'description': 'Thin or with many coarse fragments', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'SN', 'name': 'Solonetz', 'description': 'With a high content of exchangeable Na', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'VR', 'name': 'Vertisols', 'description': 'Alternating wet-dry conditions, shrink-swell clay minerals', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'SC', 'name': 'Solonchaks', 'description': 'High concentration of soluble salts', 'category': 'Soils with limitations to root growth'},

        {'SU_SYMBOL': 'GL', 'name': 'Gleysols', 'description': 'Groundwater-affected, underwater or in tidal areas', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'AN', 'name': 'Andosols', 'description': 'Allophanes and/or Al-humus complexes', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'PZ', 'name': 'Podzols', 'description': 'Subsoil accumulation of humus and/or oxides', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'PT', 'name': 'Plinthosols', 'description': 'Accumulation and redistribution of Fe', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'PL', 'name': 'Planosols', 'description': 'Stagnant water, abrupt textural difference', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'ST', 'name': 'Stagnosols', 'description': 'Stagnant water, structural difference and/or moderate textural difference', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'NT', 'name': 'Nitisols', 'description': 'Low-activity clays, P fixation, many Fe oxides, strongly structured', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'FR', 'name': 'Ferralsols', 'description': 'Dominance of kaolinite and oxides', 'category': 'Soils distinguished by Fe/Al chemistry'},

        {'SU_SYMBOL': 'CH', 'name': 'Chernozems', 'description': 'Very dark topsoil, secondary carbonates', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'KS', 'name': 'Kastanozems', 'description': 'Dark topsoil, secondary carbonates', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'PH', 'name': 'Phaeozems', 'description': 'Dark topsoil, no secondary carbonates (unless very deep), high base status', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'UM', 'name': 'Umbrisols', 'description': 'Dark topsoil, low base status', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},

        {'SU_SYMBOL': 'DU', 'name': 'Durisols', 'description': 'Accumulation of, and cementation by, secondary silica', 'category': 'Accumulation of moderately soluble salts or non-saline substances'},
        {'SU_SYMBOL': 'GY', 'name': 'Gypsosols', 'description': 'Accumulation of secondary gypsum', 'category': 'Accumulation of moderately soluble salts or non-saline substances'},
        {'SU_SYMBOL': 'CL', 'name': 'Calcisols', 'description': 'Accumulation of secondary carbonates', 'category': 'Accumulation of moderately soluble salts or non-saline substances'},

        {'SU_SYMBOL': 'RT', 'name': 'Retisols', 'description': 'Interfingering of coarser-textured, lighter-coloured material into a finer-textured, stronger coloured layer', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'AC', 'name': 'Acrisols', 'description': 'Low-activity clays, low base status', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'LX', 'name': 'Lixisols', 'description': 'Low-activity clays, high base status', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'AL', 'name': 'Alisols', 'description': 'High-activity clays, low base status', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'LV', 'name': 'Luvisols', 'description': 'High-activity clays, high base status', 'category': 'Soils with clay-enriched subsoil'},

        {'SU_SYMBOL': 'CM', 'name': 'Cambisols', 'description': 'Moderately developed', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'FL', 'name': 'Fluvisols', 'description': 'Stratified fluviatile, marine or lacustrine sediments', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'AR', 'name': 'Arenosols', 'description': 'Sandy', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'RG', 'name': 'Regosols', 'description': 'No significant profile development', 'category': 'Soils with little or no profile differentiation'},

        {'SU_SYMBOL': 'DS', 'name': 'Dunes', 'description': 'Dunes and shifting sands', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'ST', 'name': 'Salt flats', 'description': 'Salt flats', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'RD', 'name': 'Rock debris', 'description': 'Rock debris', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'WR', 'name': 'Inland waters', 'description': 'Inland waters', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'GG', 'name': 'Glaciers and snow', 'description': 'Glaciers and snow', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'UR', 'name': 'Urban', 'description': 'Urban', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'IS', 'name': 'Island', 'description': 'Island', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'NI', 'name': 'No data', 'description': 'No data', 'category': 'Miscellaneous units'},

        #--- Reassigned from FAO74 to WRB2014
        {'SU_SYMBOL': 'PD', 'name': 'Podzoluvisols (Retisols)', 'description': 'Interfingering of coarser-textured, lighter-coloured material into a finer-textured, stronger coloured layer', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'GR', 'name': 'Greyzems (Phaeozems)', 'description': 'Dark topsoil, no secondary carbonates (unless very deep), high base status', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'RK', 'name': 'Rock debris', 'description': 'Rock debris', 'category': 'Miscellaneous units'},
        ]

    df_lookup = pd.DataFrame(code_info)
    df = df_counts.merge(df_lookup, on='SU_SYMBOL', how='left')
    df = df.sort_values(by=['category', 'name'], ascending=[True, True])

    return df

def plot_counts(df_counts, plot_dir, plot_name):

    df_counts_sorted = df_counts.sort_values("count", ascending=False)

    fig = plt.figure(figsize=(8, 4))
    plt.bar(df_counts_sorted['name'], df_counts_sorted['count'], color='0')
    plt.title("Counts of WRB2014 soil orders associated with dust event origin points")
    plt.xlabel("Soil Order")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha='right')

    _plot_save(fig, plot_dir, plot_name)

    return

def _plot_save(fig, plot_dir, plot_name):
    plt.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(os.path.join(plot_dir, plot_name), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

def create_legend_png(df_counts, plot_dir, plot_name):

    fig, ax = plt.subplots(figsize=(16, 12))
    ax.set_axis_off()

    table_data = list(zip(df_counts['name'], df_counts['category'], df_counts['description']))

    table = ax.table(cellText=table_data,
                    colLabels=['Name', 'Category', 'Description'],
                    loc='center',
                    colWidths=[0.1, 0.4, 0.5])
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 1.5)

    #--- Customize all cells
    for row, cell in table.get_celld().items():
        cell.get_text().set_ha('left')   # horizontal alignment: left/center/right
        cell.get_text().set_va('center') # vertical alignment: top/center/bottom
        
    #--- Highlight the header
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_text_props(weight='bold', color='white')
            cell.set_facecolor('#000000')

    _plot_save(fig, plot_dir, plot_name)
    return

def get_wrb2014_distributions(gdf):
    #--- Filter this to American Southwest
    area_by_symbol = gdf.groupby('SU_SYMBOL')['Shape_Area'].sum().reset_index()

    return area_by_symbol

def plot_counts_and_total(df_counts, df_counts_total, plot_dir, plot_name):


    fig, ax1 = plt.subplots(figsize=(8,5))

    bars1 = ax1.bar(df_counts['name'], df_counts['count'], color='skyblue', label='Dust soil orders', alpha=0.5)
    ax1.set_ylabel('Dust event (count)')
    ax1.set_xlabel('Soil order')

    ax2 = ax1.twinx()
    bars2 = ax2.bar(df_counts_total['name'], df_counts_total['Shape_Area'], color='salmon', label='Total soil orders', alpha=0.5)
    ax2.set_ylabel('WRB soil total area (square degrees)')

    plt.title("Counts of WRB2014 soil orders")
    x = np.arange(len(df_counts_total['name']))
    ax1.set_xticks(x)
    ax1.set_xticklabels(df_counts_total['name'], rotation=45, ha='right')
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    #--- Draw vertical separators between groups
    boundaries = df_counts_total.groupby('category').size().cumsum()[:-1]
    for b in boundaries:
        ax2.axvline(b - 0.5, color='gray', linewidth=1, zorder=-1)

    _plot_save(fig, plot_dir, plot_name)
    return

def plot_map_for_sel_order(gdf, order_symbol_list, location, dust_df, plot_title, plot_dir, plot_name):
    """
    Map of a soil order overlaid with points for the dust events. 

    gdf: from open_wrb2014_file()
    order_symbol: example is "CL" for Calcisols [check add_info_to_counts()]
    order_symbol_list: ["CL", "RG", "FL"]
    """
    
    colors = ["orange", "green", "purple"]

    fig = plt.figure(figsize=(10, 8))
    ax = plt.axes(projection=ccrs.PlateCarree())

    ax.coastlines(resolution="50m", color="black", linewidth=1)
    ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=1)
    ax.add_feature(cfeature.OCEAN, facecolor="lightblue", zorder=6)

    for order, color in zip(order_symbol_list, colors):
        gdf_sel = gdf[gdf["SU_SYMBOL"] == order]

        gdf_sel.plot(
            ax=ax,
            transform=ccrs.PlateCarree(),
            facecolor=color,
            edgecolor="black",
            linewidth=0.8,
            alpha=0.7,
            zorder=1,
            label=order
        )

    ax.legend(title="Soil Order")

    #--- Plot dust points
    ax.scatter(
        dust_df["longitude"],
        dust_df["latitude"],
        transform=ccrs.PlateCarree(),
        s=6,
        marker="o",
        c="black",
        alpha=0.3,
        zorder=2
        )

    lat_min, lat_max, lon_min, lon_max = _get_coords_for_region(location)
    extent = [lon_min, lon_max, lat_min, lat_max]
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    ax.set_title(plot_title)

    _plot_save(fig, plot_dir, plot_name)
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

def open_usda_soil_types_file(filepath, location_name):
    '''
    Open the USDA .tif file
    '''
    import rioxarray as rxr
    from matplotlib.patches import Patch

    min_lat, max_lat, min_lon, max_lon = _get_coords_for_region(location_name)

    soil = (
        rxr.open_rasterio(filepath)
        .squeeze("band", drop=True)  # remove band dimension
        .rio.clip_box(
            minx=min_lon,
            miny=min_lat,
            maxx=max_lon,
            maxy=max_lat,
        )
    )


    gridcode_to_order = _get_usda_soil_type_gridcode()
    soil_order_names = np.vectorize(gridcode_to_order.get)(soil.values)

    unique_orders = np.unique(soil_order_names[~pd.isna(soil_order_names)])
    order_to_index = {name: i for i, name in enumerate(unique_orders)}
    soil_order_index = np.vectorize(order_to_index.get)(soil_order_names)
    cmap = plt.get_cmap("tab20", len(unique_orders))

    legend_elements = [
        Patch(facecolor=cmap(i), label=name)
        for i, name in enumerate(unique_orders)
    ]


    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()})

    soil.plot(
        ax=ax,
        cmap=cmap,
        add_colorbar=False,
        transform=ccrs.PlateCarree()
    )

    ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

    ax.set_title("Soil Suborders with State Boundaries")
    ax.legend(
        handles=legend_elements,
        title="Soil Order",
        bbox_to_anchor=(1.05, 1),
        loc="upper left"
    )

    _plot_save(fig, plot_dir="figures", plot_name="usda_soil_types")

    return

def _get_usda_soil_type_gridcode():
    # Mapping GRIDCODE → SOIL_ORDER
    gridcode_to_order = {
        0: "Water",
        1: "Shifting Sands",
        2: "Rocky Land",
        3: "Ice/Glacier",
        4: "Salt flats",
        5: "Gelisols",
        6: "Gelisols",
        7: "Gelisols",
        10: "Histosols",
        12: "Histosols",
        13: "Histosols",
        14: "Histosols",
        15: "Spodosols",
        16: "Spodosols",
        17: "Spodosols",
        18: "Spodosols",
        19: "Spodosols",
        21: "Andisols",
        22: "Andisols",
        23: "Andisols",
        24: "Andisols",
        25: "Andisols",
        26: "Andisols",
        27: "Andisols",
        30: "Oxisols",
        31: "Oxisols",
        32: "Oxisols",
        33: "Oxisols",
        34: "Oxisols",
        41: "Vertisols",
        42: "Vertisols",
        43: "Vertisols",
        44: "Vertisols",
        45: "Vertisols",
        50: "Aridisols",
        51: "Aridisols",
        54: "Aridisols",
        55: "Aridisols",
        56: "Aridisols",
        57: "Aridisols",
        60: "Ultisols",
        61: "Ultisols",
        62: "Ultisols",
        63: "Ultisols",
        64: "Ultisols",
        70: "Mollisols",
        71: "Mollisols",
        72: "Mollisols",
        73: "Mollisols",
        74: "Mollisols",
        75: "Mollisols",
        76: "Mollisols",
        77: "Mollisols",
        80: "Alfisols",
        81: "Alfisols",
        82: "Alfisols",
        83: "Alfisols",
        84: "Alfisols",
        90: "Inceptisols",
        91: "Inceptisols",
        92: "Inceptisols",
        93: "Inceptisols",
        94: "Inceptisols",
        95: "Inceptisols",
        101: "Entisols",
        102: "Entisols",
        103: "Entisols",
        104: "Entisols",
        200: "No data",
        201: "Urban, mining",
        202: "Human disturbed",
        204: "Fishpond",
        205: "Island",
    }

    return gridcode_to_order