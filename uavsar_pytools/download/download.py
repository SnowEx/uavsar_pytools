"""
Originally written by HP Marshall in matlab. Transcribed by Micah J. into python. Amended for uavsar_pytools by Zach Keskinen.
Functions uses the urls to download uavsar data. It will not overwrite files
so if you want to re-download fresh manually remove the output_dir.
Warning: Canceling the script mid run will produce a file partially written. Rerunning the script will think the
file is already downloaded and skip it. You will have to remove that file if you want to re-download it.
"""

import requests
import os
from os.path import join, isdir, isfile, basename, dirname, exists
from tqdm.auto import tqdm
import logging

import time

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.WARNING)

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
        if r.status_code == 401:
            log.warning(f'HTTP CODE 401. DOWNLOADING REQUIRES A NETRC FILE AND SIGNED UAVSAR END USER AGREEMENT! See ReadMe for instructions.')
        elif r.status_code == 404:
            log.warning(f'HTTP CODE 404. Url not found. Currently trying {url}.')
        else:
            log.warning(f'HTTP CODE {r.status_code}. Skipping download!')


def download_image(url, output_dir, ann = False, ann_url = None):
    """
    Downloads uavsar InSAR files from a url.
    Args:
        url (string): A url containing uavsar flight data. Can be from JPL or ASF
        output_dir (string): Directory to save the data in
    Returns:
        out_fp (string): File path to downloaded image.
    Raises:
       None
    """

    log.info(f'Starting download of {url}...')
    local = join(output_dir, basename(url))

    # Make the output dir if it doesn't exist
    if not isdir(output_dir):
        os.makedirs(output_dir)

    if not isfile(local):
        stream_download(url, local)
    else:
        log.info(f'{local} already exists, skipping download!')

    if ann:
        if ann_url == None:
            if url.split('.')[-1] == 'zip' or url.split('.')[-1] == 'ann':
                log.info('Download already contains ann file, skipping download!')
            else:
                # see if we can use the parent directory to extract the annotation file
                parent = dirname(url)
                # ASF formatting - query parent directory
                if parent.split('.')[-1] == 'zip':
                    log.debug(f'ASF url found for {url}')
                    parent_files = requests.get(parent).json()['response']
                    ann_info = [i for i in parent_files if '.ann' in i['name']][0]
                    # assert len(ann_info) == 1, 'More than one ann file detected'
                    ann_url = ann_info['url']
                    log.debug(f'Annotation url: {ann_url}')

                # Can't find zip parent directory - have to parse url to get ann
                else:
                    log.debug(f'Can not find zip parent directory.')
                    ext = url.split('.')[-1]
                    pols = ['VVVV','HHHH','HVHV', 'HHHV', 'HHVV','HVVV']
                    slc_pol = [pol for pol in pols if (pol in url)]
                    if len(slc_pol) == 1:
                        url = url.replace(slc_pol[0], '')

                    if ext == 'grd':
                        if len(basename(url).split('.')) == 2:
                            url = url.replace('.grd','.ann')
                        if len(basename(url).split('.')) == 3:
                            url = url.replace('.grd','')
                        ext = url.split('.')[-1]
                    elif ext == 'inc' and 'asf' in url:
                        url = url.replace('INC','METADATA')
                    ann_url = url.replace(f'.{ext}', '.ann')
                    log.debug(f'Parsed annotation url: {ann_url}')

                    response = requests.get(ann_url)
                    if response.status_code == 200:
                        log.debug('Success in parsing ann url')

                    else:
                        ann_url = None

                if ann_url:
                    ann_local = join(output_dir, basename(ann_url))
                    log.debug(f'Annotation local: {ann_local} and url {ann_url}')
                    if not isfile(ann_local):
                        stream_download(ann_url, ann_local)
                    else:
                        log.info(f'{ann_local} already exists, skipping download!')
                    return local, ann_local
                else:
                    log.warning('No ann url found. Manually provide .ann url.')
                    ann_url = None
        else:
            ann_local = join(output_dir, basename(ann_url))
            if not isfile(ann_local):
                stream_download(ann_url, ann_local)

        return local, None

def download_zip(url, output_dir):
    """
    Downloads uavsar InSAR files from a zip url.
    Args:
        url (string): A url containing uavsar flight zip. Can be from JPL or ASF
        output_dir (string): Directory to save the data in
    Returns:
        out_fp (string): File path to downloaded images.
    Raises:
       None
    """

    log.info(f'Starting download of {url}...')

    # Make the output dir if it doesn't exist
    if not isdir(output_dir):
        os.makedirs(output_dir)

    local = join(output_dir, basename(url))

    if not exists(local):
        stream_download(url, local)
    else:
        log.info(f'{local} already exists, skipping download!')

    return local
