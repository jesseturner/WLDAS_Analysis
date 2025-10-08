World Reference Base 2014 soils data downloaded from https://data.isric.org/geonetwork/srv/api/records/wrb2014-map.

Categories are at https://files.isric.org/public/WRB/ISRIC_WRB-map_2015_final.pdf. 

Steps for WRB2024 Counts figure:
1. Convert Line dataset to GeoDataFrame points to compare to WRB2014 shapefiles
2. Count occurances of dust events in each soil order
3. Merge counts with legend from documentation to make figure