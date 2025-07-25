import os, requests
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

class WldasData:
    def __init__(self, date):
        self.date = date
        print("Warning: WLDAS data files are large, each ~900 MB")

    def download(self):
        #--- Set .netrc with GES DISC username and password
        #--- Add a reminder if there is a no permissions error

        YYYY = self.date.strftime('%Y')
        MM = self.date.strftime('%m')
        DD = self.date.strftime('%d')

        url = f"https://hydro1.gesdisc.eosdis.nasa.gov/data/WLDAS/WLDAS_NOAHMP001_DA1.D1.0/{YYYY}/{MM}/WLDAS_NOAHMP001_DA1_{YYYY}{MM}{DD}.D10.nc"

        #--- Create session with NASA Earthdata login
        session = requests.Session()
        session.auth = (os.getenv("EARTHDATA_USERNAME"), os.getenv("EARTHDATA_PASSWORD"))

        #--- Make download directory
        download_dir = Path("WLDAS_data")
        download_dir.mkdir(parents=True, exist_ok=True)

        #--- Download file
        print(f"Connecting to {url}...")
        response = session.get(url, stream=True)
        print("Connection established. Starting download...")

        if response.status_code == 200:
            #--- Extract filename from content-disposition if present
            cd = response.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                filename = cd.split('filename=')[-1].strip('\"')
            else:
                filename = url.split('/')[-1]

            filepath = download_dir / filename

            #--- Write file to local disk
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 8192

            with open(filepath, 'wb') as f, tqdm(
                total=total_size, unit='B', unit_scale=True, desc=filename
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

            print(f"Downloaded to {filepath}")
        else:
            print(f"Failed to download: {response.status_code} {response.reason}")
            print(response.text)

