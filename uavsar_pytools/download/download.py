"""
Originally written by HP Marshall in matlab. Transcribed by Micah J. into python.
Script uses the urls, polarizations and file types to download uavsar data. It will not overwrite files
so if you want to re-download fresh manually remove the output_dir.
Warning: Canceling the script mid run will produce a file partially written. Rerunning the script will think the
file is already downloaded and skip it. You will have to remove that file if you want to re-download it.
usage:
    python3 download_uavsar.py
"""

import requests
import os
from os.path import join, isdir, isfile, basename
import progressbar
from tqdm import tqdm
import logging

log = logging.getLogger(__name__)

def stream_download(url, output_f):
    """
    Args:
        url: url to download
        output_f: path to save the data to
    """
    print(f"\n\nDownloading {url}\nSaving to {output_f}")
    r = requests.get(url, stream=True)

    if r.status_code == 200:
        #bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength)
        with open(output_f, 'wb') as f:
            for i, chunk in tqdm(enumerate(r), description = f'Downloading {basename(url)}'):
                f.write(chunk)
                #bar.update(i)
    else:
        print(f"HTTP CODE {r.status_code}. Skipping download!")


def download_InSAR(url, output_dir, polarizations=['HH', 'HV', 'VH', 'VV'],
                    file_types=['amp1', 'amp2', 'cor', 'int']):
    """
    Downloads uavsar InSAR files from a url.
    Args:
        url (string): A url containing uavsar flight data. Can be from JPL or ASF
        output_dir (string): Directory to save the data in
    Returns:
        None
    Raises:
        ValueError: If the base flight name is missing the polarization HH
    """
    log.info('Starting download of {url}...')

    local = join(output_dir, basename(url))
    # Checks for existence of url
    try:
        r = requests.get(url)
    except requests.HTTPError as e:
        log.warning(f'{url} returned {e}')

    # Make the output dir if it doesn't exist
    if not isdir(output_dir):
        os.makedirs(output_dir)

    if not isfile(local):
        stream_download(url, local)
    else:
        log.info(f"{local} already exists, skipping download!")

    # Download the ann file always.
    ext = url.split('.')[-2]
    ann_url = url.replace(f"{ext}.grd", "ann")
    ann_local = local.replace(f"{ext}.grd", "ann")

    if not isfile(ann_local):
        stream_download(ann_url, ann_local)
    else:
        log.info(f"{ann_local} already exists, skipping download!")


def main():
    url = 'https://unzip.asf.alaska.edu/INTERFEROMETRY_GRD/UA/grmesa_27416_21011-010_21016-002_0021d_s01_L090_01_int_grd.zip/grmesa_27416_21011-010_21016-002_0021d_s01_L090HH_01.cor.grd'
    download_InSAR(url, '../../data/')

main()
