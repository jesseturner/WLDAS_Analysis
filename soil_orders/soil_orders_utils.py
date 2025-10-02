import geopandas as gpd
import os, glob
import matplotlib.pyplot as plt

def open_wrb2014_file(wrb2014_file_dir, plot_dir, plot_path):
    shapefiles = glob.glob(os.path.join(wrb2014_file_dir, "*.shp"))
    layers = [gpd.read_file(shp) for shp in shapefiles]
    print(f"Loaded {len(layers)} shapefiles")

    fig, ax = plt.subplots(figsize=(10, 10))
    for gdf in layers:
        gdf.plot(ax=ax)
    _plot_save(fig, plot_dir, plot_path)    
    return

def _plot_save(fig, plot_dir, plot_path):
    plt.tight_layout()
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(plot_path)
    plt.close(fig)

    return