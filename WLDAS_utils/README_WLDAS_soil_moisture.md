Repo: https://github.com/jesseturner/spectral_analysis

Hypothesis: Soil moisture trends in a recognizable pattern before and after dust blows from the area. 

Overview:
- Data downloaded from https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS
- For each dust case in the Line dust dataset, we create a time list of soil moistures associated with the single nearest WLDAS grid point 
- We plot the average soil moisture for dust events over time (30 days before to 30 days after) 
- Regional splits are done using the regional boxes from Line 2025. 

Using the code: `WLDAS_utils/wldas_utils.py`. 

Instructions for getting WDLAS subset:
1. https://disc.gsfc.nasa.gov/datasets?keywords=WLDAS
2. Subset directory
3. Download list of links
4. Earthdata authentication:
    * `.netrc` with username and password
    * `.urs_cookies` created
    * `.dodsrc` with path to cookies and netrc
5. Add subset text file to directory `<url.txt>`
6. `wget --load-cookies ~/.urs_cookies --save-cookies ~/.urs_cookies --keep-session-cookies --content-disposition -i '<url.txt>'`