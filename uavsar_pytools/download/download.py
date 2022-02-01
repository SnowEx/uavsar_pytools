"""
Originally written by HP Marshall in matlab. Transcribed by Micah J. into python.
Script uses the urls to download uavsar data. It will not overwrite files
so if you want to re-download fresh manually remove the output_dir.
Warning: Canceling the script mid run will produce a file partially written. Rerunning the script will think the
file is already downloaded and skip it. You will have to remove that file if you want to re-download it.
usage:
    python3 download_uavsar.py
"""

import requests
import os
from os.path import join, isdir, isfile, basename, dirname
from tqdm import tqdm
import logging

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

def stream_download(url, output_f):
    """
    Args:
        url: url to download
        output_f: path to save the data to
    """

    r = requests.get(url, stream=True)
    if r.status_code == 200:
        # Progress bar - https://towardsdatascience.com/how-to-download-files-using-python-part-2-19b95be4cdb5
        total_size= int(r.headers.get('content-length', 0))
        with open(output_f, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True , desc=f'Downloading {basename(url)}') as pbar:
                for ch in r.iter_content(chunk_size=1024):
                    if ch:
                        f.write(ch)
                        pbar.update(len(ch))
    else:
        log.warning(f'HTTP CODE {r.status_code}. Skipping download!')


def download_InSAR(url, output_dir, ann = False):
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

    log.info(f'Starting download of {url}...')
    local = join(output_dir, basename(url))
    # # Checks for existence of url
    # try:
    #     r = requests.get(url)
    # except requests.HTTPError as e:
    #     log.warning(f'{url} returned {e}')

    # Make the output dir if it doesn't exist
    if not isdir(output_dir):
        os.makedirs(output_dir)

    if not isfile(local):
        stream_download(url, local)
    else:
        log.info(f'{local} already exists, skipping download!')

    if ann:
        if url.split('.')[-1] == 'zip':
            log.info('Zip dowloads already contains ann file, skipping download!')
        else:
            parent = dirname(url)
            #log.debug(parent)
            parent_files = requests.get(parent).json()['response']
            log.debug(parent_files)
            ann_info = [i for i in parent_files if '.ann' in i['name']][0]
            # assert len(ann_info) == 1, 'More than one ann file detected'
            ann_url = ann_info['url']
            ann_local = join(output_dir, ann_info['name'])

        # if len(basename(url).split('.')) == 2:
        #     # Download the ann file.
        #     ext = url.split('.')[-1]
        #     ann_url = url.replace(f'{ext}', 'ann')
        #     ann_local = local.replace(f'{ext}', 'ann')


        # elif len(basename(url).split('.')) == 3:
        #     # Download the ann file.
        #     ext = url.split('.')[-2]
        #     grd_slc = url.split('.')[-1]
        #     ann_url = url.replace(f'{ext}.{grd_slc}', 'ann')
        #     ann_local = local.replace(f'{ext}.{grd_slc}', 'ann')
        log.debug(f'Annotation local: {ann_local} and {ann_url}')
        if not isfile(ann_local):
            stream_download(ann_url, ann_local)
        else:
            log.info(f'{ann_local} already exists, skipping download!')


def main():
    url = 'https://unzip.asf.alaska.edu/INTERFEROMETRY_GRD/UA/grmesa_27416_21011-010_21016-002_0021d_s01_L090_01_int_grd.zip/grmesa_27416_21011-010_21016-002_0021d_s01_L090HH_01.cor.grd'
    #url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/lowman_05208_21019-019_21021-007_0006d_s01_L090_01_int_grd.zip'
    #url = 'https://datapool.asf.alaska.edu/INC/UA/Rosamd_35012_21067_013_211124_L090_CX_01.inc'
    ann_url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090_CX_01.ann'
    #url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090VVVV_CX_01.mlc'
    download_InSAR(url, '../../data/', ann = True)

main()
