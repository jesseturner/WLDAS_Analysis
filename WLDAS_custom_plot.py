#--- Custom code, not included in utils
#--- Plot histograms: the WLDAS histogram and the dust-specific histogram

import matplotlib.pyplot as plt
import glob
import pickle

all_data_file_paths = glob.glob("WLDAS_hist/all_data*.pkl")
all_data = []
for path in all_data_file_paths:
    with open(path, 'rb') as f:
        data = pickle.load(f)
        all_data.append(data)
print(all_data)

# with open(f"WLDAS_hist/{hist_name}_{self.date.strftime('%Y%m%d')}.pkl", "rb") as f:
#             hist_store = pickle.load(f)
#         os.makedirs("WLDAS_hist_plots", exist_ok=True)
#         for variable in self.ds.data_vars:
#             if variable not in hist_store:
#                 print(f"Skipping '{variable}' — no histogram stored.")
#                 continue

#             long_name, units, counts, bin_edges = hist_store[variable]
#             bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

#             fig, ax1 = plt.subplots(figsize=(10, 5))

#             plt.figure(figsize=(8, 4))
#             plt.bar(bin_centers, counts, width=np.diff(bin_edges), align="center", edgecolor="blue", color='blue', alpha=0.7,)
#             plt.title(f"Histogram of {variable} ({long_name})")
#             plt.xlabel(f"{units}")
#             plt.ylabel("Frequency")
#             plt.tight_layout()
#             plt.savefig(f"WLDAS_hist_plots/{hist_name}_{variable}.png")
#             plt.close()


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