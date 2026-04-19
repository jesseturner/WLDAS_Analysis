#--- Using the dust and non-dust tables created with 2026-04-16, 
#--- finding the moisture distributions over 10 m/s winds

import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np

def main():
    dust_path = "data/processed/dust_and_non_dust/dust.csv"
    non_dust_path = "data/processed/dust_and_non_dust/non_dust.csv"

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

    fig, ax_bar = plt.subplots(figsize=(12, 6))

    plt.hist(df_dust["moisture"], bins=20, 
            alpha=0.5, 
            color="tab:orange",
            edgecolor="black",
            linewidth=1,
            label="dust events", 
            density=True)
    
    plt.hist(df_non_dust["moisture"], bins=20, 
        alpha=0.5, 
        color="tab:blue",
        label="non-dust grid",
        density=True)

    # ax_bar.set_xticklabels(counts_df.index, rotation=45, ha="right")
    ax_bar.set_ylabel("Fraction of total")
    ax_bar.set_xlabel("Soil Moisture (0-10 cm) [m³/m³]")
    ax_bar.set_title("Soil Moisture at Winds >= 10 m/s")

    ax_bar.legend()
    plt.tight_layout()
    plt.savefig(os.path.join("figures", "moisture_bar_chart_threshold"), bbox_inches='tight', dpi=300)
    plt.close(fig)

    return

#------------------------

if __name__ == "__main__":
    main()