import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import rioxarray as rxr
from pyproj import CRS, Transformer
import os
import rasterio

from modules_texture import gldas_texture_utils as gldas
from modules_soil_orders import soil_orders_utils as orders
from modules_line_dust import line_dust_utils as dust


def main():
    #--- DUST
    print("Plotting contour map with dust points...")

    location_name = "American Southwest"
    dust_path = "data/raw/line_dust/dust_dataset_final_20241226.txt"
    dust_df = dust.read_dust_data_into_df(dust_path)
    dust_df = dust.filter_to_region(dust_df, location_name)    

    plot_dust_point_contour_map(dust_df, location_name)

    #--- TEXTURES
    print("Plotting soil texture map...")

    gldas_path = "data/raw/gldas_soil_texture/GLDASp5_soiltexture_025d.nc4"
    texture_ds = gldas.open_gldas_file(gldas_path)
    texture_ds = gldas.filter_to_region(texture_ds, location_name)

    plot_gldas_soil_texture_map(texture_ds, location_name)

    #--- SOIL TYPES
    print("Plotting soil type map...")

    usda_filepath = "data/raw/soil_types_usda/global-soil-suborders-2022.tif"
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)

    soil_da = (
        rxr.open_rasterio(usda_filepath)
        .squeeze("band", drop=True)
        .rio.clip_box(
            minx=min_lon,
            miny=min_lat,
            maxx=max_lon,
            maxy=max_lat,
        )
    )
    plot_usda_soil_types_map(soil_da, location_name)

    #--- LAND COVER
    print("Plotting land cover map...")

    cec_filepath = ("data/raw/cec_land_cover/NA_NALCMS_landcover_2020v2_30m/data/NA_NALCMS_landcover_2020v2_30m.tif")
    cec_full = rxr.open_rasterio(cec_filepath).squeeze("band", drop=True)
    cec_ds = get_cec_land_cover_reprojection(cec_full, location_name)
    plot_land_cover_map(cec_ds, location_name)

    return

#------------------------

def get_texture_map_features():
    texture_dict = gldas.get_texture_dict()

    # texture_colors = [
    #     "#f4e7b0",  # Sand
    #     "#e6d591",  # Loamy Sand
    #     "#d9c070",  # Sandy Loam
    #     "#c0b080",  # Silt Loam
    #     "#b0a070",  # Silt
    #     "#a67c52",  # Loam
    #     "#b77c4d",  # Sandy Clay Loam
    #     "#9c6644",  # Silty Clay Loam
    #     "#805533",  # Clay Loam
    #     "#8c3f2f",  # Sandy Clay
    #     "#6e2f23",  # Silty Clay
    #     "#4f1f18",  # Clay
    #     "#1a1a1a",  # Organic Matter
    #     "#3399ff",  # Water
    #     "#808080",  # Bedrock
    #     "#454545",  # Other
    # ]

    texture_colors = [
        "#EE6352",  # Sand
        "#e6d591",  # Loamy Sand
        "#d9c070",  # Sandy Loam
        "#c0b080",  # Silt Loam
        "#b0a070",  # Silt
        "#a67c52",  # Loam
        "#16DB93",  # Sandy Clay Loam
        "#9c6644",  # Silty Clay Loam
        "#805533",  # Clay Loam
        "#8c3f2f",  # Sandy Clay
        "#048BA8",  # Silty Clay
        "#4f1f18",  # Clay
        "#1a1a1a",  # Organic Matter
        "#d8fbff",  # Water
        "#808080",  # Bedrock
        "#454545",  # Other
    ]

    #--- Remove water
    del texture_dict[14]
    del texture_colors[13]

    soil_cmap = ListedColormap(texture_colors, name="soil_textures")
    return soil_cmap, texture_colors, texture_dict

def plot_gldas_soil_texture_map(texture_ds, location_name):

    soil_cmap, texture_colors, texture_dict = get_texture_map_features()

    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()})

    texture_da = texture_ds.GLDAS_soiltex

    texture_da.plot(
        ax=ax,
        cmap=soil_cmap,
        add_colorbar=False,
        transform=ccrs.PlateCarree()
    )

    add_squares_to_plot(ax)

    ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)
    min_lat, max_lat, min_lon, max_lon = gldas._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    
    ax.set_title("Soil Textures with Dust Origins")
    legend_handles = [
        Patch(facecolor=color, edgecolor="black", label=label)
        for label, color in zip(texture_dict.values(), texture_colors)
    ]

    dust_handle = Patch(
        facecolor="white",
        edgecolor="black",
        label="Dust Origin"
    )
    ax.legend(
        handles=legend_handles + [dust_handle],
        title="Soil Texture",
        loc="lower left",
        frameon=True
    )

    gldas._plot_save(fig, fig_dir="figures", fig_name="gldas_texture_categories")

    return

def get_soil_order_indices(soil_da):
    #--- Get colormap associated with soil order names
    #------ Colormaps not synced up due to spatial plot not following
    soil_order_dict = orders.get_soil_order_dict() 
    category_colors = orders.get_category_colors()

    unique_orders = list(dict.fromkeys(soil_order_dict.values()))
    order_to_index = {order: i for i, order in enumerate(unique_orders)}
    colors = [category_colors[o] for o in unique_orders]
    cmap = mcolors.ListedColormap(colors)
    n_categories = len(unique_orders)
    norm = mcolors.BoundaryNorm(boundaries=np.arange(-0.5, n_categories+0.5, 1), ncolors=n_categories)

    default_order = "No data"
    flat_values = soil_da.values.ravel()
    flat_indices = np.array([
        order_to_index.get(soil_order_dict.get(int(code), default_order), order_to_index[default_order])
        for code in flat_values
    ])
    soil_indices = soil_da.copy()
    soil_indices.values = flat_indices.reshape(soil_da.shape)

    return unique_orders, cmap, norm, colors, soil_indices

def plot_usda_soil_types_map(soil_da, location_name):

    unique_orders, cmap, norm, colors, soil_indices = get_soil_order_indices(soil_da)

    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()})

    soil_indices.plot(
        ax=ax,
        cmap=cmap,
        norm=norm,
        add_colorbar=False,
        transform=ccrs.PlateCarree()
    )

    add_squares_to_plot(ax)

    ax.add_feature(cfeature.STATES, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
    
    ax.set_title("USDA Soil Orders with Dust Origins")

    unique_indices = np.unique(soil_indices.values)
    legend_elements = [
        Patch(facecolor=colors[i], label=name)
        for i, name in enumerate(unique_orders)
        if i in unique_indices
    ]

    ax.legend(
        handles=legend_elements,
        title="Soil Type",
        loc="lower left",
        frameon=True
    )

    orders._plot_save(fig, plot_dir="figures", plot_name="usda_soil_types")
    return

def get_cec_land_cover_reprojection(cec_full, location_name):
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    min_lat_extend = min_lat - 5
    max_lat_extend = max_lat + 4

    src_crs = CRS.from_epsg(4326) 
    dst_crs = CRS.from_wkt(cec_full.rio.crs.to_wkt()) 
    transformer = Transformer.from_crs(src_crs, dst_crs, always_xy=True) 
    minx, miny = transformer.transform(min_lon, min_lat_extend) 
    maxx, maxy = transformer.transform(max_lon, max_lat_extend) 
    minx, maxx = sorted([minx, maxx]) 
    miny, maxy = sorted([miny, maxy]) 
    cec_cropped = cec_full.rio.clip_box(minx=minx, miny=miny, maxx=maxx, maxy=maxy)

    output_path = "data/processed/cec_land_cover/cec_land_cover_SW_epsg4326.tif"
    if not os.path.exists(output_path):
        print("Reprojecting to lat/lon...") 
        cec = cec_cropped.rio.reproject( 
            "EPSG:4326", 
            resolution=0.05, 
            resampling=rasterio.enums.Resampling.nearest)
        cec.rio.to_raster(output_path)
    else:
        print("Processed raster already exists — skipping reprojection.")
        cec = rxr.open_rasterio(output_path).squeeze("band", drop=True)

    return cec
def get_land_cover_plot_features(cec_ds):
    classes = {
        1: ("Temp/Sub-polar Needleleaf Forest", "#1b5e20"),
        2: ("Sub-polar Taiga Needleleaf Forest", "#2e7d32"),
        3: ("Tropical Broadleaf Evergreen Forest", "#388e3c"),
        4: ("Tropical Broadleaf Deciduous Forest", "#66bb6a"),
        5: ("Temp/Sub-polar Broadleaf Deciduous Forest", "#81c784"),
        6: ("Mixed Forest", "#4caf50"),
        7: ("Tropical/Sub-tropical Shrubland", "#7a554f"),
        8: ("Temp/Sub-polar Shrubland", "#a28073"),
        9: ("Tropical/Sub-tropical Grassland", "#e4f451"),
        10: ("Temp/Sub-polar Grassland", "#9db72b"),
        11: ("Sub-polar Shrub–Lichen–Moss", "#b0bec5"),
        12: ("Sub-polar Grass–Lichen–Moss", "#90a4ae"),
        13: ("Sub-polar Barren–Lichen–Moss", "#78909c"),
        14: ("Wetland", "#26c6da"),
        15: ("Cropland", "#e7cd24"),
        16: ("Barren Lands", "#F60707"),
        17: ("Urban and Built-up", "#0e0100"),
        18: ("Water", "#1e88e5"),
        19: ("Snow and Ice", "#e0f7fa"),
    }

    codes = np.array(sorted(classes))
    names = [classes[c][0] for c in codes]
    colors = [classes[c][1] for c in codes]

    cmap = mcolors.ListedColormap(colors)
    cec_ds = cec_ds.where(np.isin(cec_ds, codes)) #--- Null values are not included
    norm = mcolors.BoundaryNorm(
        boundaries=np.append(codes - 0.5, codes[-1] + 0.5),
        ncolors=len(colors),
    )
    return cec_ds, cmap, norm, names, colors

def plot_land_cover_map(cec_ds, location_name):

    cec_ds, cmap, norm, names, colors = get_land_cover_plot_features(cec_ds)

    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()},)

    cec_ds.plot(
        ax=ax,
        transform=ccrs.PlateCarree(),
        cmap=cmap,
        norm=norm,
        add_colorbar=False,
    )

    add_squares_to_plot(ax)

    ax.set_title("Land Cover Categories with Dust Origins")

    ax.add_feature(cfeature.STATES, linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, zorder=4)
    ax.add_feature(cfeature.BORDERS, linewidth=0.8)
    ax.add_feature(cfeature.OCEAN, facecolor='white', zorder=3)
    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

    legend_handles = [
        Patch(color=color, label=name)
        for name, color in zip(names, colors)
    ]

    ax.legend(
        handles=legend_handles,
        title="Land Cover Class",
        loc="lower left",
        frameon=True
    )
    
    plt.tight_layout()
    orders._plot_save(fig, plot_dir="figures", plot_name="cec_land_cover")

    return

def plot_dust_point_contour_map(dust_df, location_name):
    
    fig, ax = plt.subplots(figsize=(16, 12), subplot_kw={"projection": ccrs.PlateCarree()},)

    #--- Plot dust points
    ax.scatter(
        dust_df["longitude"],
        dust_df["latitude"],
        transform=ccrs.PlateCarree(),
        s=12,
        marker="o",
        facecolors='#e7cd24',
        edgecolors='#e7cd24',
        linewidth=1, 
        alpha=0.5,
        zorder=6
    )

    add_squares_to_plot(ax)

    ax.set_title("Blowing dust origin points with contours (2001-2020)")

    ax.add_feature(cfeature.STATES, edgecolor='white', linewidth=2, zorder=2)
    ax.add_feature(cfeature.BORDERS, edgecolor='white', linewidth=2, zorder=2)
    ax.add_feature(cfeature.OCEAN, facecolor='white', zorder=3)
    ax.add_feature(cfeature.LAND, facecolor='black', zorder=1)

    min_lat, max_lat, min_lon, max_lon = orders._get_coords_for_region(location_name)
    ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())

    plt.tight_layout()
    orders._plot_save(fig, plot_dir="figures", plot_name="dust_contour_points")

    return

def add_squares_to_plot(ax):
    import matplotlib.patches as patches

    regions = {
        "Region 1": [(31.75, -107.65), (31.25, -107.15)],  # 252 events
        "Region 2": [(31.50, -108.20), (31.00, -107.70)],  # 157 events
        "Region 3": [(40.05, -118.75), (39.55, -118.25)],  # 154 events
        "Region 4": [(31.00, -107.35), (30.50, -106.85)],  # 137 events
        "Region 5": [(41.15, -119.25), (40.65, -118.75)],  # 111 events
        "Region 6": [(30.85, -106.80), (30.35, -106.30)],  # 93 events
        "Region 7": [(33.00, -102.40), (32.50, -101.90)],  # 78 events
        "Region 8": [(33.30, -102.90), (32.80, -102.40)],  # 65 events
        "Region 9": [(35.60, -111.00), (35.10, -110.50)],  # 62 events
        "Region 10": [(33.00, -106.45), (32.50, -105.95)],  # 58 events
        "Region 11": [(37.95, -106.05), (37.45, -105.55)],  # 52 events
        "Region 12": [(40.70, -119.80), (40.20, -119.30)],  # 50 events
        "Region 13": [(34.15, -103.10), (33.65, -102.60)],  # 50 events
        "Region 14": [(29.50, -107.05), (29.00, -106.55)],  # 49 events
        "Region 15": [(36.10, -108.85), (35.60, -108.35)],  # 47 events
        "Region 16": [(32.50, -102.00), (32.00, -101.50)],  # 46 events
        "Region 17": [(30.85, -108.00), (30.35, -107.50)],  # 45 events
        "Region 18": [(38.10, -117.90), (37.60, -117.40)],  # 43 events
        "Region 19": [(32.35, -107.90), (31.85, -107.40)],  # 42 events
        "Region 20": [(36.90, -110.10), (36.40, -109.60)],  # 41 events
        "Region 21": [(31.15, -108.85), (30.65, -108.35)],  # 41 events
        "Region 22": [(28.95, -107.00), (28.45, -106.50)],  # 41 events
        "Region 23": [(31.50, -107.15), (31.00, -106.65)],  # 40 events
        "Region 24": [(33.50, -102.40), (33.00, -101.90)],  # 40 events
        "Region 25": [(32.20, -110.10), (31.70, -109.60)],  # 33 events
        "Region 26": [(41.80, -117.15), (41.30, -116.65)],  # 32 events
        "Region 27": [(36.20, -111.45), (35.70, -110.95)],  # 29 events
        "Region 28": [(29.55, -107.90), (29.05, -107.40)],  # 29 events
        "Region 29": [(30.35, -107.75), (29.85, -107.25)],  # 24 events
        "Region 30": [(29.50, -106.55), (29.00, -106.05)],  # 24 events
        "Region 31": [(31.25, -104.95), (30.75, -104.45)],  # 24 events
        "Region 32": [(29.10, -104.90), (28.60, -104.40)],  # 24 events
        "Region 33": [(38.90, -113.40), (38.40, -112.90)],  # 23 events
        "Region 34": [(34.00, -102.60), (33.50, -102.10)],  # 23 events
        "Region 35": [(38.25, -104.50), (37.75, -104.00)],  # 22 events
        "Region 36": [(31.45, -104.00), (30.95, -103.50)],  # 21 events
        "Region 37": [(32.75, -102.90), (32.25, -102.40)],  # 21 events
        "Region 38": [(33.05, -101.90), (32.55, -101.40)],  # 21 events
        "Region 39": [(32.00, -108.50), (31.50, -108.00)],  # 20 events
        "Region 40": [(30.35, -107.05), (29.85, -106.55)],  # 20 events
        "Region 41": [(34.40, -103.60), (33.90, -103.10)],  # 20 events
        "Region 42": [(26.90, -104.20), (26.40, -103.70)],  # 19 events
        "Region 43": [(40.35, -120.35), (39.85, -119.85)],  # 17 events
        "Region 44": [(32.10, -115.50), (31.60, -115.00)],  # 16 events
        "Region 45": [(39.15, -112.85), (38.65, -112.35)],  # 16 events
        "Region 46": [(33.20, -116.20), (32.70, -115.70)],  # 15 events
    }

    for name, ((lat1, lon1), (lat2, lon2)) in regions.items():

        min_lat = min(lat1, lat2)
        max_lat = max(lat1, lat2)
        min_lon = min(lon1, lon2)
        max_lon = max(lon1, lon2)
        
        width = max_lon - min_lon
        height = max_lat - min_lat
        
        rect = patches.Rectangle(
            (min_lon, min_lat),
            width,
            height,
            linewidth=3,
            edgecolor='white',
            facecolor='none',
            zorder=9,
            transform=ccrs.PlateCarree()
        )
        
        ax.add_patch(rect)

    return

#------------------------

if __name__ == "__main__":
    main()