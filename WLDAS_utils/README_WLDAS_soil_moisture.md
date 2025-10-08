Repo: https://github.com/jesseturner/spectral_analysis

Hypothesis: Soil moisture trends in a recognizable pattern before and after dust blows from the area. 

Overview:
- Data downloaded from https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS
- For each dust case in the Line dust dataset, we create a time list of soil moistures associated with the single nearest WLDAS grid point 
- We plot the average soil moisture for dust events over time (30 days before to 30 days after) 
- Regional splits are done using the regional boxes from Line 2025. 

Using the code: `WLDAS_utils/wldas_utils.py`. 

Data is initially downloaded to `WLDAS_data_subset` 
using the `get_wldas_data_bulk_subset()` method 
and the .txt file in the repository. 

For each dust case in the Line dust dataset, 
we create a time list of soil moistures 
associated with the nearest WLDAS grid point 
using `get_wldas_plus_minus_30()`. This is saved 
as a JSON file in `WLDAS_plus_minus_30`. 

We can plot the soil moisture record (30 days before to 30 days after) 
for individual cases with `plot_wldas_plus_minus_30()`.

We can plot the combined soil moisture pattern
with dust events centered at the 0 day mark 
using `get_wldas_plus_minus_30_average()` and 
`plot_wldas_plus_minus_30_average()`. 