import geopandas as gpd
import os, glob
import pandas as pd
import matplotlib.pyplot as plt

def open_wrb2014_file(wrb2014_file_dir, plot_dir, plot_path):
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

def count_total(gdf_regions):
    counts_df = gdf_regions.groupby('SU_SYMBOL').size().reset_index(name='count')
    
    return counts_df

def add_info_to_counts(df_counts):
    code_info = [
        {'SU_SYMBOL': 'AC', 'name': 'Acrisols', 'description': 'Low-activity clays, low base status', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'AR', 'name': 'Arenosols', 'description': 'Sandy', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'CH', 'name': 'Chernozems', 'description': 'Very dark topsoil, secondary carbonates', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'CL', 'name': 'Calcisols', 'description': 'Accumulation of secondary carbonates', 'category': 'Accumulation of moderately soluble salts or non-saline substances'},
        {'SU_SYMBOL': 'CM', 'name': 'Cambisols', 'description': 'Moderately developed', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'DS', 'name': 'Dunes', 'description': 'Dunes and shifting sands', 'category': 'Miscellaneous units'},
        {'SU_SYMBOL': 'FL', 'name': 'Fluvisols', 'description': 'Stratified fluviatile, marine or lacustrine sediments', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'GL', 'name': 'Gleysols', 'description': 'Groundwater-affected, underwater or in tidal areas', 'category': 'Soils distinguished by Fe/Al chemistry'},
        {'SU_SYMBOL': 'KS', 'name': 'Kastanozems', 'description': 'Dark topsoil, secondary carbonates', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'LP', 'name': 'Leptosols', 'description': 'Thin or with many coarse fragments', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'LV', 'name': 'Luvisols', 'description': 'High-activity clays, high base status', 'category': 'Soils with clay-enriched subsoil'},
        {'SU_SYMBOL': 'PH', 'name': 'Phaeozems', 'description': 'Dark topsoil, no secondary carbonates (unless very deep), high base status', 'category': 'Pronounced accumulation of organic matter in the mineral topsoil'},
        {'SU_SYMBOL': 'RG', 'name': 'Regosols', 'description': 'No significant profile development', 'category': 'Soils with little or no profile differentiation'},
        {'SU_SYMBOL': 'SN', 'name': 'Solonetz', 'description': 'With a high content of exchangeable Na', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'VR', 'name': 'Vertisols', 'description': 'Alternating wet-dry conditions, shrink-swell clay minerals', 'category': 'Soils with limitations to root growth'},
        {'SU_SYMBOL': 'WR', 'name': 'Inland waters', 'description': 'Inland waters', 'category': 'Miscellaneous units'},
        ]

    df_lookup = pd.DataFrame(code_info)
    df = df_counts.merge(df_lookup, on='SU_SYMBOL', how='left')
    df = df.sort_values(by=['category', 'name'], ascending=[True, True])

    return df

def plot_counts(df_counts, plot_dir, plot_path):

    fig = plt.figure(figsize=(8, 4))
    plt.bar(df_counts['name'], df_counts['count'], color='0')
    plt.title("Counts of WRB2014 soil orders associated with dust event origin points")
    plt.xlabel("Soil Order")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha='right')

    _plot_save(fig, plot_dir, plot_path)
    return

def _plot_save(fig, plot_dir, plot_path):
    plt.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(plot_path, bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

def create_legend_png(df_counts, plot_dir, plot_path):

    fig, ax = plt.subplots(figsize=(16, 6))
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

    _plot_save(fig, plot_dir, plot_path)
    return