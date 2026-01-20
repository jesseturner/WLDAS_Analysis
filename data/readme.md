### WLDAS soil moisture

Currently stored at `/mnt/data2/jturner/wldas_data/`, due to large file sizes. 

Downloaded by subset using files in `raw/wldas_soil_moisture/`.

Instructions for getting WDLAS soil moisture subset:
1. https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS
2. Subset directory
3. Download list of links
4. Earthdata authentication:
    * `.netrc` with username and password
    * `.urs_cookies` created
    * `.dodsrc` with path to cookies and netrc
5. Add subset text file to directory `<url.txt>`
6. `wget --load-cookies ~/.urs_cookies --save-cookies ~/.urs_cookies --keep-session-cookies --content-disposition -i '<url.txt>'`

### WRB soil orders

World Reference Base 2014 soils data downloaded from https://data.isric.org/geonetwork/srv/api/records/wrb2014-map.

Categories are at https://files.isric.org/public/WRB/ISRIC_WRB-map_2015_final.pdf. 

Steps for WRB2024 Counts figure:
1. Convert Line dataset to GeoDataFrame points to compare to WRB2014 shapefiles
2. Count occurences of dust events in each soil order
3. Merge counts with legend from documentation to make figure

### GLDAS soil texture

Data source: https://ldas.gsfc.nasa.gov/gldas/soils

WLDAS does not seem to have this same dataset, not sure why. 
* WLDAS seems to use STATSGO/FAO soils map (https://ldas.gsfc.nasa.gov/wldas/parameters), which is similar but doesn't give fractions
* GLDAS uses global soils dataset of Reynolds, Jackson, and Rawls (WRR2000)

### Soil types USDA 

Data source: https://nrcs.app.box.com/s/2ag3jwmwk3a1ybtrwd2w4koqflgkd5xz/folder/266083012079?page=2

### CEC land cover

Data source: https://www.cec.org/north-american-environmental-atlas/land-cover-30m-2020/