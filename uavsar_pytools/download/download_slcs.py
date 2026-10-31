"""
Find and download UAVSAR single look complex stacks from the JPL data portal.

ASF does not serve SLC stacks. `get_uavsar_slcs` uses the ASF catalogue only to
find which flights exist for a site and date range, then resolves the JPL release
folder that holds each flight line and returns download ready urls.
`download_uavsar_slcs` fetches those urls.
"""
import os
import logging
import asf_search as asf
import requests
from collections import defaultdict

from uavsar_pytools.download.download import stream_download
from uavsar_pytools.campaigns import site_code

log = logging.getLogger(__name__)

# JPL stack host. Numbered release folders live here; which one holds a given
# flight line is not published, so it is found by probing newest first.
JPL_BASE_URL = 'https://downloaduav2.jpl.nasa.gov'
RELEASE_FOLDERS = [f'Release{r}' for r in range(54, 14, -1)]
TAGS = ['BU', 'BC']


def _probe(url):
    """'file' if url serves a data file, 'missing' if it does not. Raises
    ConnectionError when the host does not answer, so callers stop probing."""
    try:
        response = requests.head(url, allow_redirects=True, timeout=30)
    except requests.RequestException as e:
        raise ConnectionError(f'JPL download host is not answering ({url}): {e}') from None
    # The JPL web server answers unknown paths with an html page, so status alone is not enough
    if response.status_code == 200 and 'text/html' not in response.headers.get('Content-Type', ''):
        return 'file'
    return 'missing'


def _find_release(flight_folder, first_file):
    """Release folder and BC/BU tag under which a flight line's stack is served,
    or None when no release folder holds it (wrong version or unreleased)."""
    for release in RELEASE_FOLDERS:
        for tag in TAGS:
            url = f'{JPL_BASE_URL}/{release}/{flight_folder}/{first_file.format(tag=tag)}'
            if _probe(url) == 'file':
                log.info(f'{flight_folder} found in {release} with tag {tag}')
                return release, tag
    return None


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
    Find UAVSAR flights at ASF and return the JPL download urls of their SLC stacks.

    Parameters
    ----------
    flight_name : str
        Campaign name or site code, e.g. 'Lowman, CO' or 'lowman'.
    flight_num : str, optional
        Keep only this flight line, e.g. '05208'. Default None keeps all lines.
    getann, getdop, getllh, getlkv : bool, optional
        Also return the annotation, doppler, lat/lon/height and look vector files.
    start_date, end_date : str, optional
        ASF search window, 'YYYY-MM-DD'.
    pol : list of str, optional
        Polarizations. Default ['HH'].
    seg : list of str, optional
        Segments. Default ['s1', 's2', 's3'].
    pxlsp : list of str, optional
        Multilook factors. Default ['2x8'].
    version : int, optional
        JPL stack version. Default 1.

    Returns
    -------
    dict
        {'<site>_<flight line>': [urls]}. Flight lines whose stack is not found
        on JPL at this version are logged and left out.

    Raises
    ------
    ConnectionError
        When the JPL download host does not answer.
    ValueError
        When no requested flight line can be found on JPL.
    """
    site = site_code(flight_name)
    log.info(f'Getting SLC stacks for {flight_name} ({site}).')

    # ASF no longer indexes campaign or beam mode for UAVSAR; search by site code
    grans = asf.search(platform='UAVSAR', processingLevel=['POLSAR'],
                       granule_list=[f'{site}_*'], start=start_date, end=end_date,
                       maxResults=5000)
    log.info(f'{len(grans)} ASF granules found for {site}')

    # Build the file names of each flight line with a {tag} placeholder for BC/BU
    v = str(version).zfill(2)
    names = defaultdict(list)
    for g in grans:
        parts = g.properties['sceneName'].split('_')
        if parts[0] == 'UA':
            parts = parts[1:]
        # e.g. lowman_05208_21021_007_210322_L090_CX_01
        site, flight_line, flight_id, date, band = parts[0], parts[1].zfill(5), f'{parts[2]}_{parts[3]}', parts[4], parts[5]
        if flight_num is not None and flight_line != str(flight_num).zfill(5):
            continue

        files = []
        for p in pol:
            base = f'{site}_{flight_line}_{flight_id}_{date}_{band}{p}_{v}_{{tag}}'
            for s in seg:
                for pxl in pxlsp:
                    files.append(f'{base}_{s}_{pxl}.slc')
                    if getllh:
                        files.append(f'{site}_{flight_line}_{v}_{{tag}}_{s}_{pxl}.llh')
                    if getlkv:
                        files.append(f'{site}_{flight_line}_{v}_{{tag}}_{s}_{pxl}.lkv')
            if getann:
                files.append(f'{base}.ann')
            if getdop:
                files.append(f'{site}_{flight_line}_{v}_{{tag}}.dop')

        key = f'{site}_{flight_line}'
        for f in files:
            if f not in names[key]:
                names[key].append(f)

    # Resolve the release folder once per flight line and expand to urls
    links = {}
    for key, files in names.items():
        flight_folder = f'{key}_{v}'
        found = _find_release(flight_folder, files[0])
        if found is None:
            log.error(f'{flight_folder} not found on JPL: version {version} may not exist')
            continue
        release, tag = found
        links[key] = [f'{JPL_BASE_URL}/{release}/{flight_folder}/{f.format(tag=tag)}' for f in files]
        log.info(f'{key}: {len(links[key])} files')

    if names and not links:
        raise ValueError(f'No flight line of {site} version {version} found on JPL')
    return links


def download_uavsar_slcs(urls: list, out_dir: str):
    """
    Download urls from `get_uavsar_slcs` into out_dir, skipping files already there.
    """
    if not urls:
        log.warning('No urls provided to download.')
        return
    if not isinstance(urls, list) or not all(isinstance(u, str) and u.startswith('http') for u in urls):
        raise TypeError('urls must be a list of http urls from get_uavsar_slcs')

    os.makedirs(out_dir, exist_ok=True)
    for url in urls:
        filename = os.path.join(out_dir, url.split('/')[-1])
        if os.path.exists(filename):
            log.info(f'{filename} already exists. Skipping download.')
            continue
        log.info(f'Downloading {url}')
        stream_download(url, filename)
