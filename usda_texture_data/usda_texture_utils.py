import pandas as pd

def _open_usda_texture_csv(usda_filepath):
    df = pd.read_csv(usda_filepath)
    return df

def counts_of_usda_texture_values(usda_filepath):
    df = _open_usda_texture_csv(usda_filepath)
    counts = df["SAMPLE_1"].value_counts().sort_index().to_dict()

    soil_mapping = {
        1: "Clay",
        2: "Clay loam",
        3: "Loam",
        4: "Loamy sand",
        5: "Sand",
        6: "Sandy clay",
        7: "Sandy clay loam",
        8: "Sandy loam",
        9: "Silt",
        10: "Silty clay",
        11: "Silty clay loam",
        12: "Silt loam"
    }

    counts_named = {soil_mapping[k].lower().replace(" ", "_"): v for k, v in counts.items()}

    return counts_named



