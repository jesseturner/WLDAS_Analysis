### Surface variables and dust

This repository (initially named WLDAS_Analysis) is to support the 2026 paper on surface variables associated with dust. 

Data sources: 
* Line 2025 dust dataset
* Wind u and v from NARR (hourly)
* Soil moisture from WLDAS (daily)
* Soil texture from GLDAS
* Soil orders from WRB 2014
* Surface cover from CEC

All data downloaded on `jturner@polarbear3:/home/jturner/WLDAS_Analysis`
* run using conda env `wldas_env`

Process data with functions in `DATA/`:
1. `process_moisture_grid.py` Create a coarsened moisture grid (otherwise processing is errors out from memory limits, WLDAS data is very high resolution)
2. `process_wind_grid_narr.py` Create wind dataset for "daytime max wind speed" from u and v (currently using NARR version)
3. `process_dust_points_vars.py` Create a dataframe for each dust event with colocated winds, moisture, soil texture, soil order, and surface cover
4. `control_grid.py` Create an xarray dataset for all the variables from 2001-2020, spaced over the moisture grid (highest resolution dataset)
5. `control_grid_dust_sites.py` Create an xarray dataset for all the variables from 2001-2020, but only at dust sites
6. `process_time_trend.py` Create a dataframe of dust events and the 30 days of moisture before and after
7. `surface_combo_dust.py` Create xarray dataset with combined ID from soil texture + soil order + surface cover from 2001-2020

Run analysis using `ANALYSIS` jupyter notebooks:
* plug in required processed datasets from `DATA/processed/`