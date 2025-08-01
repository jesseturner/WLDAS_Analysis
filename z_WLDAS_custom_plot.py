#--- Custom code, not included in utils
#--- Plot histograms: the WLDAS histogram and the dust-specific histogram

import matplotlib.pyplot as plt
import glob
import pickle
import numpy as np
import os

os.makedirs("WLDAS_hist_plots", exist_ok=True)

#--- Get variable keys
sample_data = "WLDAS_hist/all_data_20010102.pkl"
with open(sample_data, 'rb') as f:
    data = pickle.load(f)
    keys = data.keys()

print(keys)


#--- Set variable of interest
var = 'Evap_tavg'
master_bins = np.linspace(-.5e-5, 2e-5, 60)
long_name = ''
units = ''

#--- Combine histograms: all data
all_data_file_paths = glob.glob("WLDAS_hist/all_data*.pkl")
all_data_master_counts = np.zeros(len(master_bins) - 1)

for path in all_data_file_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
        hist = data[var]

        long_name = hist[0]
        units = hist[1]
        counts = np.array(hist[2])
        bin_edges = np.array(hist[3])
        
        # Reconstruct original data points by using bin centers and weights
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        data_points = np.repeat(bin_centers, counts)

        # Re-bin to master bins
        new_counts, _ = np.histogram(data_points, bins=master_bins)

        # Accumulate
        all_data_master_counts += new_counts

print(all_data_master_counts)

#--- Combine histograms: dust points
dust_points_file_paths = glob.glob("WLDAS_hist/dust_points*.pkl")
dust_points_master_counts = np.zeros(len(master_bins) - 1)

for path in dust_points_file_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
        hist = data[var]

        counts = np.array(hist[2])
        bin_edges = np.array(hist[3])
        
        bin_centers = 0.5 * (bin_edges[:-1] + bin_edges[1:])
        data_points = np.repeat(bin_centers, counts)

        new_counts, _ = np.histogram(data_points, bins=master_bins)

        dust_points_master_counts += new_counts


#--- Plotting histograms 

fig, ax1 = plt.subplots(figsize=(10, 5))

bin_centers = (master_bins[:-1] + master_bins[1:]) / 2

ax1.bar(bin_centers, all_data_master_counts, width=np.diff(master_bins), align="center", edgecolor="blue", color='blue', alpha=0.6, label="WLDAS Data")
ax1.set_title(f"Histogram of {var} ({long_name})")
ax1.set_xlabel(f"{units}")
ax1.set_ylabel("Frequency")
ax1.grid(True)

ax2 = ax1.twinx()
ax2.bar(bin_centers, dust_points_master_counts, width=np.diff(master_bins), align="center", edgecolor="orange", color='orange', alpha=0.6, label="WLDAS Data for dust region")

fig.legend(loc="upper right")
plt.savefig(f"WLDAS_hist_plots/{var}.png", dpi=200, bbox_inches='tight')
plt.close()




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