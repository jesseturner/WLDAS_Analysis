#--- Using the dust and non-dust tables created with 2026-04-16, 
#--- finding the moisture distributions over 10 m/s winds

import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np

def main():
    dust_path = "data/processed/dust_and_non_dust/dust.csv"
    non_dust_path = "data/processed/dust_and_non_dust/non_dust_at_sites.csv"

    df_dust = pd.read_csv(dust_path)
    df_non_dust = pd.read_csv(non_dust_path)

    df_dust = wind_threshold(threshold_num=10, df=df_dust)
    df_non_dust = wind_threshold(threshold_num=10, df=df_non_dust)

    plot_bar_chart(df_dust, df_non_dust)

    return

#------------------------

def wind_threshold(threshold_num, df):
    '''
    :param threshold_num: wind speed in m/s (10)
    :param df: dust_df or non_dust_df
    '''
    print(f"Filtering dataframe to wind speeds >= {threshold_num}...")
    filtered_df = df[df["wind_speed"] >= threshold_num]
    print(f"Originally {df.shape}, now filtered to {filtered_df.shape}...")

    return filtered_df



def plot_bar_chart(df_dust, df_non_dust):
    print("Plotting bar chart...")

    #--- Calculate bins
    bins = np.linspace(0, 0.4, 30)
    counts_dust, _ = np.histogram(df_dust["moisture"], bins=bins)
    counts_non_dust, _ = np.histogram(df_non_dust["moisture"], bins=bins)
    width = (bins[1] - bins[0]) / 3
    density_dust = counts_dust / np.sum(counts_dust)
    density_non_dust = counts_non_dust / np.sum(counts_non_dust)

    fig, ax_bar = plt.subplots(figsize=(12, 6))

    plt.bar(bins[:-1], density_dust, 
            width=width, 
            align='edge', 
            color="tab:orange",
            edgecolor="black",
            linewidth=1,
            label=f"dust events \n n={len(df_dust["moisture"]) :.2e}",)
    plt.bar(bins[:-1] + width, density_non_dust, 
            width=width, 
            align='edge', 
            color="tab:blue",
            label=f"non-dust grid \n n={len(df_non_dust["moisture"]) :.2e}",
            alpha=0.5)

    # plt.hist(df_dust["moisture"], bins=20, 
    #         alpha=0.5, 
    #         color="tab:orange",
    #         edgecolor="black",
    #         linewidth=1,
    #         label="dust events", 
    #         density=True)
    
    # plt.hist(df_non_dust["moisture"], bins=20, 
    #     alpha=0.5, 
    #     color="tab:blue",
    #     label="non-dust grid",
    #     density=True)

    # ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
    medians = get_medians(df_dust, df_non_dust)
    add_medians_to_plot(ax_bar, medians)
    ax_bar.set_ylabel("Fraction of total", fontsize=18)
    ax_bar.set_xlabel("Soil Moisture (0-10 cm) [m³/m³]", fontsize=18)
    ax_bar.set_title("Soil Moisture at Winds >= 10 m/s", fontsize=24)

    ax_bar.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("figures", "moisture_bar_chart_threshold"), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

def add_medians_to_plot(ax_bar, medians):

    ax_bar.axvline(
        medians[0],
        color="tab:orange",
        linestyle="--",
        linewidth=2,
        zorder=0
    )
    ax_bar.text(x=medians[0], 
                y=0.93,
                s=f'{medians[0]:.2f}', 
                color="tab:orange",
                alpha=0.8, 
                fontsize=10,
                fontweight='bold',
                rotation=90,
                verticalalignment='center',
                horizontalalignment='right',
                transform=ax_bar.get_xaxis_transform())

    ax_bar.axvline(
        medians[1],
        color="tab:blue",
        linestyle="--",
        linewidth=2,
        zorder=0
    )
    
    ax_bar.text(x=medians[1], 
                y=0.93,
                s=f'{medians[1]:.2f}', 
                color="tab:blue",
                alpha=0.8, 
                fontsize=10,
                fontweight='bold',
                rotation=90,
                verticalalignment='center',
                horizontalalignment='right',
                transform=ax_bar.get_xaxis_transform())
    
    return

def get_medians(df_dust, df_non_dust):
    median_dust = df_dust["moisture"].median(skipna=True)
    median_non_dust = df_non_dust["moisture"].median(skipna=True)

    medians = median_dust, median_non_dust

    return medians

#------------------------

if __name__ == "__main__":
    main()