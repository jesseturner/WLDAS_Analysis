Repo: https://github.com/jesseturner/spectral_analysis

Hypothesis: Dust regions show different frequency distributions of certain surface variables compared to the entire US Southwest. 

Overview:
- Data downloaded from https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS
- We create a frequency distribution of the variables over the whole region (latitudes from 27.5 to 44, longitudes from -128 to -100)
- We create a frequency distribution of the variable over regions that have been recorded as a dust origin (0.1 deg x 0.1 deg squares). This is visualized in 0_masking_example (on Google Drive). 
- Both methods use the full time range from 2001-2020. 

Using the code: `WLDAS_utils/wldas_utils.py`. 

Results in `WLDAS_hist_plots`. Using WLDAS data from 2001-2020. 


