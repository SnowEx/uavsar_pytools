import os
import logging
import numpy as np
import asf_search as asf
import requests
import datetime
from collections import defaultdict


# Import the native download function from the repo
from uavsar_pytools.download.download import stream_download

# Initialize the logger
log = logging.getLogger(__name__)

def get_uavsar_slcs(
    flight_name: str, 
    flight_num: str = None,
    getann: bool = False, 
    getdop: bool = False,
    getllh: bool = False,
    getlkv: bool = False,
    start_date: str = '2020-01-01',
    end_date: str = '2021-12-31',
    pol: list = ['HH'],
    seg: list = ['s1', 's2', 's3'],
    pxlsp: list = ['2x8'],
    version: int = 1
) -> dict: 
    """
    Query the ASF DAAC for UAVSAR flight lines and generate a dictionary of JPL download URLs.

    This function maps a given UAVSAR campaign name to its corresponding ASF search string, 
    retrieves the metadata for the specified date range, and constructs the expected filenames
    for the JPL Release 30 data portal.

    Parameters
    ----------
    flight_name : str
        The abbreviation or full name of the UAVSAR campaign (e.g., 'lowman' or 'Lowman, CO').
    flight_num : str, optional
        Specific flight line number to filter the search. Default is None (returns all lines).
    getann : bool, optional
        If True, appends the annotation (.ann) file URL for each flight. Default is False.
    start_date : str, optional
        Start date for the ASF search in 'YYYY-MM-DD' format. Default is '2020-01-01'.
    end_date : str, optional
        End date for the ASF search in 'YYYY-MM-DD' format. Default is '2021-12-31'.
    pol : list of str, optional
        List of polarization bands to include. Default is ['HH'].
    sec : list of str, optional
        List of data segments/swaths to include. Default is ['s1', 's2', 's3'].
    pxlsp : list of str, optional
        Pixel spacing strings to append to the filename. Default is ['2x8'].
    version : int, optional
        Version number to download. Default is 1. Note that if version number is invalid, 
        no error will be raised until download_uavsar_slcs is called. 

    Returns
    -------
    dict
        A defaultdict where keys are formatted as '{flight_abbr}_{flight_line}' and values 
        are lists of constructed JPL filenames/URLs.

    Raises
    ------
    ValueError
        If the provided `flight_name` is not found in the valid campaigns mapping.
    """
    links = defaultdict(list)

    campaigns = { # SnowEx campaigns and abbreviations
        'grmesa': 'Grand Mesa, CO',
        'lowman': 'Lowman, CO',
        'fraser': 'Fraser, CO',
        'irnton': 'Ironton, CO',                    # Senator Beck Basin
        'peeler': 'Peeler Peak, CO',                # East River
        'rockmt': 'Rocky Mountains NP, CO',         # Cameron Pass
        'silver': 'Silver City, ID',                # Reynolds Creek
        'uticam': 'Utica, MT',                      # Central Ag Research Center
        'stlake': 'Salt Lake City, UT',             # Little Cottonwood Canyon
        'alamos': 'Los Alamos, NM',                 # Jemez River
        'dorado': 'Eldorado National Forest, CA',   # American River Basin
        'donner': 'Donner Memorial State Park, CA', # Sagehen Creek
        'sierra': 'Sierra National Forest, CA'      # Lakes Basin
    }

    if flight_name not in campaigns.values():
        try: 
            flight_abbr = flight_name 
            flight_name = campaigns[flight_name]
        except KeyError:
            raise ValueError(f"Invalid flight name: {flight_name}. Valid options are: {campaigns}")
    else: 
        flight_abbr = next((k for k, v in campaigns.items() if v == flight_name), None)
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log.info(f"{current_time}")
    log.info(f'Getting files for {flight_name} ({flight_abbr}).')

    if flight_num is None: 
        grans = asf.search(platform='UAVSAR', 
                           campaign=flight_name, 
                           beamMode='POL',
                           start=start_date,
                           end=end_date)
    else: 
        grans = asf.search(platform='UAVSAR', 
                           campaign=flight_name, 
                           flightLine=flight_num,
                           beamMode='POL',
                           start=start_date,
                           end=end_date)

    log.info(f"{len(grans)} granules found for {flight_name}")
    
    flight_lines = set()

    for g in grans: 
        scene_name = g.properties["sceneName"]
        parts = scene_name.split("_")
        
        site = parts[1]
        flight_line = parts[2].zfill(5)
        flight_lines.add(flight_line)
        
        flight1_id = parts[3] + '_' + parts[4]
        band = parts[6]
        v = str(version).zfill(2)
        date1 = parts[5]

        # append filenames to the list of urls to download 
        for p in pol: 
            urls = []
            for s in seg: 
                for pxl in pxlsp:
                    f1_base = f"{site}_{flight_line}_{flight1_id}_{date1}_{band}{p}_{v}_[BC/BU]"

                    urls.append(f"{f1_base}_{s}_{pxl}.slc")

                    # this will cause some repeats, since there is only one per seg
                    if getllh: 
                        urls.append(f"{site}_{flight_line}_{v}_[BC/BU]_{s}_{pxl}.llh")
                    if getlkv: 
                        urls.append(f"{site}_{flight_line}_{v}_[BC/BU]_{s}_{pxl}.lkv")

            if getann: 
                urls.append(f"{f1_base}.ann")
            if getdop: 
                    urls.append(f"{site}_{flight_line}_{v}_[BC/BU].dop")

            dict_key = f'{flight_abbr}_{flight_line}'
            for url in urls:
                if url not in links[dict_key]:
                    links[dict_key].append(url)

    return links


def download_uavsar_slcs(files: list, out_dir: str): 
    """
    Download UAVSAR files from the JPL data portal to a specified local directory.

    This function constructs the download URL for each file, checks for proper release folders 
    (handling 404 HTML redirects from JPL gracefully), and utilizes the package's native 
    `stream_download` method to fetch the data. It skips files that already exist locally.

    Parameters
    ----------
    files : list of str
        A list of UAVSAR filenames generated by `get_uavsar_slcs`.
    out_dir : str
        The absolute or relative path to the local directory where files will be saved.

    Returns
    -------
    None
        Outputs are saved directly to disk. Function logs the progress and status of downloads.
    """
    def is_html(link):
        try:
            # stream=true fetches the headers without downloading the whole file
            response = requests.get(link, stream=True)
            content_type = response.headers.get('Content-Type', '')
            response.close()
            return 'text/html' in content_type
        except requests.RequestException as e:
            log.error(f"Failed to check link {link}: {e}")
            return False

    BASE_URL = 'https://downloaduav2.jpl.nasa.gov'
    releases = np.arange(15, 55)[::-1]  
    RELEASE_FOLDERS = [f'Release{r}' for r in releases]

    # check for empty list
    if not files:
        log.warning("No files provided to download.")
        return
    if type(files) is not list:
        log.error(f"Files parameter should be a list of filenames, got type {type(files)} instead.")
        return
    if type(files[0]) is not str:
        log.error(f"Files list should contain strings (filenames), got type {type(files[0])} instead.")
        return

    # very basic check for filename structure 
    parts = files[0].split('_')
    tag_idx = next((i for i, p in enumerate(parts) if p.startswith('[BC/BU]')), None)
    if tag_idx is None or tag_idx < 3:
        log.error(f"Filename {files[0]} was not recognized as a valid UAVSAR filename.")
        return
    flight_folder = f"{parts[0]}_{parts[1]}_{parts[tag_idx - 1]}"

    # find valid release folder
    release_folder = None
    tag = None
    for r in RELEASE_FOLDERS:
        # for i in range(5):
        tags = ['BU', 'BC']
        for t in tags:
            url = f'{BASE_URL}/{r}/{flight_folder}/{files[0]}'
            url = url.replace('[BC/BU]', t)
            log.info(f"Trying release folder {r} and tag {t}: {url}")
            if not is_html(url):
                log.info(f'Found valid link, using {r}, {t} for download.')
                release_folder = r
                tag = t
                break
        if release_folder: 
            break 

    if not release_folder:
        log.error("Could not find a valid release folder for these files. The Release " + 
                  "folder may be out-of-range, or you may have tried to download a " + 
                  "version that doesn't exist.")
        return

    # download files
    for f in files:
        f = f.replace('[BC/BU]', tag)
        link = f'{BASE_URL}/{release_folder}/{flight_folder}/{f}'
        
        if is_html(link):
            log.warning(f"Link {link} appears to be an HTML page. Skipping download.")
            continue
            
        filename = os.path.join(out_dir, f)
        log.info(f'Checking for {filename}')
        
        if os.path.exists(filename):
            log.info(f"File {filename} already exists. Skipping download.")
            continue
            
        log.info(f"Downloading {f} to {out_dir}...")
        stream_download(link, f"{out_dir}/{f}")
