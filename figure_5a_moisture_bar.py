from modules_soil_orders import soil_orders_utils as soil_orders

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

#--- Processing or importing of wldas_total and wldas_dust is in 2026-02-18

def plot_bar_chart_moisture(wldas_total, wldas_dust):
    #--- Define bins
    bins = np.linspace(0, 0.5, 21)  # 0.0, 0.05, ..., 0.5
    bin_labels = [f"{round(bins[i],2)}-{round(bins[i+1],2)}" for i in range(len(bins)-1)]

    print("Flatten data and remove NaNs...")
    wldas_total = wldas_total['SoilMoi00_10cm_tavg'].values.flatten()
    wldas_total = wldas_total[~np.isnan(wldas_total)]
    wldas_dust = wldas_dust['SoilMoi00_10cm_tavg'].values.flatten()
    wldas_dust = wldas_dust[~np.isnan(wldas_dust)]

    print("Compute histogram counts...")
    counts_total, _ = np.histogram(wldas_total, bins=bins)
    counts_dust, _ = np.histogram(wldas_dust, bins=bins)

    fraction_total = counts_total / counts_total.sum()
    fraction_dust = counts_dust / counts_dust.sum()

    print("Prepare dataframe for plotting...")
    counts_df = pd.DataFrame({
        "Full domain": fraction_total,
        "Dust regions": fraction_dust
    }, index=bin_labels)

    print("Plotting bar chart...")
    fig_bar, ax_bar = plt.subplots(figsize=(12, 6))
    x = np.arange(len(counts_df))
    width = 0.35

    for i, bin_label in enumerate(counts_df.index):
        ax_bar.bar(
            x[i] - width / 2, counts_df.loc[bin_label, "Dust regions"],
            width, color="tab:orange", edgecolor="black", linewidth=1,
            label="Dust regions" if i == 0 else ""
        )
        ax_bar.bar(
            x[i] + width / 2, counts_df.loc[bin_label, "Full domain"],
            width, color="tab:blue", alpha=0.5,
            label="Full domain" if i == 0 else ""
        )

    ax_bar.set_xticks(x)
    ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
    ax_bar.set_ylabel("Fraction of total")
    ax_bar.set_xlabel("Soil Moisture (0-10 cm) [m³/m³]")
    ax_bar.set_title("Soil Moisture Distribution: Dust Regions vs Full Domain")
    ax_bar.legend()

    soil_orders._plot_save( fig_bar, plot_dir="figures", plot_name="soil_moisture_bar_chart" )
    return
