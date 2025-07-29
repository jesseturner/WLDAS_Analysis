#--- Custom code, not included in utils
#--- Plot histograms: the WLDAS histogram and the dust-specific histogram

import matplotlib.pyplot as plt
import glob
import pickle
import numpy as np
import os

os.makedirs("WLDAS_hist_plots", exist_ok=True)

all_data_file_paths = glob.glob("WLDAS_hist/all_data*.pkl")
all_data = []
for path in all_data_file_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
        all_data.append(data)

dust_points_file_paths = glob.glob("WLDAS_hist/dust_points*.pkl")
dust_points = []
for path in dust_points_file_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
        dust_points.append(data)

#--- I currently have a list of dictionaries, each with the variables as keys and different bins. 
#--- Transpose the list of dictionaries/keys to a list a keys/dictionaries with the histograms from each day. 
#--- This should then work for the function below. 

#--- This function should combine the histograms, if I can get a list for each variable. 
def create_combined_histogram(histograms):
    # 1. Get global bin range
    all_edges = np.concatenate([np.array(h["bin_edges"]) for h in histograms])
    global_min = all_edges.min()
    global_max = all_edges.max()

    # 2. Create common bin edges
    num_bins = 50
    common_bins = np.linspace(global_min, global_max, num_bins + 1)
    combined_counts = np.zeros(num_bins)

    # 3. Re-bin and sum counts
    for hist in histograms:
        counts = np.array(hist["count"])
        bins = np.array(hist["bin_edges"])
        
        # Compute bin centers for original
        bin_centers = (bins[:-1] + bins[1:]) / 2

        # Redistribute to common bins
        rebinned_counts, _ = np.histogram(bin_centers, bins=common_bins, weights=counts)
        
        # Accumulate
        combined_counts += rebinned_counts

    # Result
    combined_hist = {
        "long_name": histograms[0]["long_name"],
        "units": histograms[0]["units"],
        "count": combined_counts.tolist(),
        "bin_edges": common_bins.tolist(),
    }
    
    return combined_hist

for dict_all, dict_dust in zip(all_data, dust_points):
    print(dict_all.keys())
    # for var in dict_all.keys():
    #     print(var)
#         long_name, units, counts_all, bin_edges_all = dict_all[var]
#         long_name, units, counts_dust, bin_edges_dust = dict_dust[var]
#         print(long_name, units)

#         fig, ax1 = plt.subplots(figsize=(10, 5))

#         bin_centers_all = (bin_edges_all[:-1] + bin_edges_all[1:]) / 2
#         bin_centers_dust = (bin_edges_dust[:-1] + bin_edges_dust[1:]) / 2

#         ax1.bar(bin_centers_all, counts_all, width=np.diff(bin_edges_all), align="center", edgecolor="blue", color='blue', alpha=0.7, label="WLDAS Data")
#         ax1.set_title(f"Histogram of {var} ({long_name})")
#         ax1.set_xlabel(f"{units}")
#         ax1.set_ylabel("Frequency")
#         ax1.grid(True)

#         ax2 = ax1.twinx()
#         ax2.bar(bin_centers_dust, counts_dust, width=np.diff(bin_edges_dust), align="center", edgecolor="orange", color='orange', alpha=0.7, label="WLDAS Data for dust region")



#         plt.savefig(f"WLDAS_hist_plots/{var}_{var}.png", dpi=200, bbox_inches='tight')
#         plt.close()

#-------------OLD CODE

# for var in data_WLDAS_all.keys():
#     if len(data_WLDAS_dust[var]) > 0:
#         fig, ax1 = plt.subplots(figsize=(10, 5))

#         # Determine the common range for x-axis
#         x_min, x_max = np.nanmin(data_WLDAS_all[var]), np.nanmax(data_WLDAS_all[var])

#         # First histogram on primary y-axis
#         ax1.hist(data_WLDAS_all[var], bins=50, range=[x_min, x_max], edgecolor="blue", color='blue', alpha=0.7, label="WLDAS Data")
#         ax1.set_ylabel("Frequency (WLDAS Data)", color="black")
#         ax1.tick_params(axis='y', labelcolor="black")
#         #ax1.set_xlim(x_min, x_max)

#         # Create a second y-axis
#         ax2 = ax1.twinx()
#         ax2.hist(data_WLDAS_dust[var], bins=50, range=[x_min, x_max], edgecolor="orange", color='orange', alpha=0.7, label="Dust Region")
#         ax2.set_ylabel("Frequency (Dust Region)", color="orange")
#         ax2.tick_params(axis='y', labelcolor="orange")
#         #ax2.set_xlim(x_min, x_max)

#         label = label_dict.get(var, "Unknown Label")
#         fig.legend(loc="upper right")
#         ax1.set_title(f"Histogram of {label}")
#         ax1.grid(True)
        
#         # Sanitize the variable name to avoid invalid characters in filenames
#         clean_var_name = f"{var.replace(' ', '_')}"
#         clean_var_name = re.sub(r'[^A-Za-z0-9_-]', '', clean_var_name)
        
#         # Save the figure
#         fig.savefig(f"{npz_path}/{clean_var_name}.png", dpi=200, bbox_inches='tight')
#         plt.close()