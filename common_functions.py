import matplotlib.colors as mcolors
from matplotlib.colors import ListedColormap
import numpy as np

def _get_coords_for_region(location_name):
    '''
    Get the lat and lon range from the dictionary of regions used in Line 2025. 
    '''
    locations = {
        #"American Southwest": [(44, -128), (27.5, -100)], #--- Older version
        "American Southwest": [(43, -124), (25, -97)],

        "Chihuahua": [(33.3, -110.0), (28.0, -105.3)],
        "West Texas": [(35.0, -104.0), (31.8, -100.5)],
        "Central High Plains": [(43.0, -105.0), (36.5, -98.0)],
        "Nevada": [(43.0, -120.7), (37.0, -114.5)],
        "Utah": [(42.0, -114.5), (37.5, -109.0)],
        "Southern California": [(37.0, -119.0), (30.0, -114.2)],
        "Colorado Plateau": [(37.5, -112.5), (34.4, -107.0)],
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

def get_texture_map_features():
    texture_dict = get_texture_dict()

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

def get_texture_dict():
    texture_dict = {
            1: "Sand",
            2: "Loamy Sand",
            3: "Sandy Loam",
            4: "Silt Loam",
            5: "Silt",
            6: "Loam",
            7: "Sandy Clay Loam",
            8: "Silty Clay Loam",
            9: "Clay Loam", 
            10: "Sandy Clay",
            11: "Silty Clay",
            12: "Clay", 
            13: "Organic Matter",
            14: "Water", 
            15: "Bedrock",
            16: "Other",
        }
    return texture_dict

def get_land_cover_features():

    land_cover_dict = get_land_cover_dict()

    land_cover_colors = {
        1: "#1b5e20",
        2: "#2e7d32",
        3: "#388e3c",
        4: "#66bb6a",
        5: "#81c784",
        6: "#4caf50",
        7: "#7a554f",
        8: "#a28073",
        9: "#e4f451",
        10: "#9db72b",
        11: "#b0bec5",
        12: "#90a4ae",
        13: "#78909c",
        14: "#26c6da",
        15: "#e7cd24",
        16: "#F60707",
        17: "#0e0100",
        18: "#1e88e5",
        19: "#e0f7fa",
    }
    
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
        11: ("Sub-polar Shrub-Lichen-Moss", "#b0bec5"), 
        12: ("Sub-polar Grass-Lichen-Moss", "#90a4ae"), 
        13: ("Sub-polar Barren-Lichen-Moss", "#78909c"), 
        14: ("Wetland", "#26c6da"), 
        15: ("Cropland", "#e7cd24"), 
        16: ("Barren Lands", "#F60707"), 
        17: ("Urban and Built-up", "#0e0100"), 
        18: ("Water", "#1e88e5"), 
        19: ("Snow and Ice", "#e0f7fa"), }
    
    return land_cover_dict, land_cover_colors, classes

def get_land_cover_dict():
    land_cover_dict = {
        1: "Temp/Sub-polar Needleleaf Forest",
        2: "Sub-polar Taiga Needleleaf Forest",
        3: "Tropical Broadleaf Evergreen Forest",
        4: "Tropical Broadleaf Deciduous Forest",
        5: "Temp/Sub-polar Broadleaf Deciduous Forest",
        6: "Mixed Forest",
        7: "Tropical/Sub-tropical Shrubland",
        8: "Temp/Sub-polar Shrubland",
        9: "Tropical/Sub-tropical Grassland",
        10: "Temp/Sub-polar Grassland",
        11: "Sub-polar Shrub–Lichen–Moss",
        12: "Sub-polar Grass–Lichen–Moss",
        13: "Sub-polar Barren–Lichen–Moss",
        14: "Wetland",
        15: "Cropland",
        16: "Barren Lands",
        17: "Urban and Built-up",
        18: "Water",
        19: "Snow and Ice",
    }
    return land_cover_dict

def get_soil_order_names_major():
    soil_order_names_major = {
        0: "Alfisols",
        1: "Andisols", 
        2: "Aridisols",
        3: "Entisols", 
        4: "Gelisols",
        5: "Histosols", 
        6: "Inceptisols",
        7: "Mollisols",
        8: "Oxisols", 
        9: "Spodosols", 
        10: "Ultisols",
        11: "Vertisols",
        12: "Rocky Land", 
        13: "Salt flats", 
        14: "Shifting Sands",
        15: "Water", 
        16: "Ice/Glacier", 
        17: "No data", 
        18: "Urban, mining", 
        19: "Human disturbed",
        20: "Fishpond", 
        21: "Island",  
    }
    return soil_order_names_major

def get_soil_order_colors_major():

    soil_order_colors = {
        0: "#06dd0a",
        1: "#f603d6", 
        2: "#f1af4c",
        3: "#dc5908", 
        4: "#730ef8",
        5: "#61310d", 
        6: "#cada9c",
        7: "#046a2b",
        8: "#ff0e0e", 
        9: "#f084e0", 
        10: "#f9ec3a",
        11: "#1411f5",
        12: "#6b6969", 
        13: "#e0e0e0", 
        14: "#a8a6a4",
        15: "#a3d2f3", 
        16: "#aec7e8", 
        17: "#ffffff", 
        18: "#7f7f7f", 
        19: "#000000",
        20: "#1f77b4", 
        21: "#aec7e8"}

    return soil_order_colors