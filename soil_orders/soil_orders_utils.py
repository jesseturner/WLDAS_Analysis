import geopandas as gpd
import os, glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Point
import geopandas as gpd

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

    fig = plt.figure(figsize=(8, 4))
    plt.bar(df_counts['name'], df_counts['count'], color='0')
    plt.title("Counts of WRB2014 soil orders associated with dust event origin points")
    plt.xlabel("Soil Order")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha='right')

    _plot_save(fig, plot_dir, plot_name)
    return

def _plot_save(fig, plot_dir, plot_name):
    plt.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(plot_name, bbox_inches='tight', dpi=300)
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