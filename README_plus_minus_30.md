Using `WLDAS_utils/wldas_utils.py`. 

Data is initially downloaded to `WLDAS_data_subset` 
using the `get_wldas_data_bulk_subset()` method 
and the .txt file in the directory. 

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