"""
Originally written by HP Marshall in matlab. Transcribed by Micah J. into python. Amended for uavsar_pytools by Zach Keskinen.
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
        if url.split('.')[-1] == 'zip' or url.split('.')[-1] == 'ann':
            log.info('Download already contains ann file, skipping download!')
        else:
            parent = dirname(url)
            log.debug(parent)
            # ASF formatting - query parent directory
            if parent.split('.')[-1] == 'zip':
                log.debug(f'ASF url found for {url}')
                parent_files = requests.get(parent).json()['response']
                log.debug(f'Results of JSON request: {parent_files}')
                ann_info = [i for i in parent_files if '.ann' in i['name']][0]
                # assert len(ann_info) == 1, 'More than one ann file detected'
                ann_url = ann_info['url']
                log.debug(f'Annotation url: {ann_url}')

            # JPL formatting - have to parse url to get ann
            elif 'uavsar.asfdaac.alaska.edu' in url:
                log.debug(f'JPL url found for {url}')
                ext = url.split('.')[-1]
                pols = ['VVVV','HHHH','HVHV', 'HHHV', 'HHVV','HVVV']
                slc_pol = [pol for pol in pols if (pol in url)]
                if len(slc_pol) == 1:
                    url = url.replace(slc_pol[0], '')
                if ext == 'grd':
                    url = url.replace('.grd','')
                    ext = url.split('.')[-1]
                ann_url = url.replace(f'{ext}', 'ann')
                log.debug(f'Annotation url: {ann_url}')

            else:
                log.warning('No ann url found. Unable to download ann file.')
                ann_url = None

            if ann_url:
                ann_local = join(output_dir, basename(ann_url))
                log.debug(f'Annotation local: {ann_local} and {ann_url}')
                if not isfile(ann_local):
                    stream_download(ann_url, ann_local)
                else:
                    log.info(f'{ann_local} already exists, skipping download!')


def main():
    ## Testing ASF
    #url = 'https://unzip.asf.alaska.edu/INTERFEROMETRY_GRD/UA/grmesa_27416_21011-010_21016-002_0021d_s01_L090_01_int_grd.zip/grmesa_27416_21011-010_21016-002_0021d_s01_L090HH_01.cor.grd'
    #url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/lowman_05208_21019-019_21021-007_0006d_s01_L090_01_int_grd.zip'
    # url = 'https://datapool.asf.alaska.edu/INC/UA/Rosamd_35012_21067_013_211124_L090_CX_01.inc'
    # url = 'https://datapool.asf.alaska.edu/SLOPE/UA/Rosamd_35012_21067_013_211124_L090_CX_01.slope'
    # url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090_CX_01.ann'
    #url = 'https://unzip.asf.alaska.edu/STOKES/UA/Rosamd_35012_21067_013_211124_L090_CX_01_stokes.zip/Rosamd_35012_21067_013_211124_L090_CX_01.dat'
    #url = 'https://datapool.asf.alaska.edu/PAULI/UA/Rosamd_35012_21067_013_211124_L090_CX_01_pauli.tif'
    #url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090VVVV_CX_01.mlc'

    ## Testing JPL
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090HHHH_CX_01.mlc'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.dat'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090HHVV_CX_01.grd' ##didnt work
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.inc'
    url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.slope'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.hgt'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.ann'
    # url =  'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.mlc'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.cor'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.amp2.grd'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.ann'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090VVVV_CX_01.mlc'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090HHHV_CX_01.grd'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.inc'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.slope'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.amp1'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.ann'
    download_InSAR(url, '../../data/', ann = True)

main()
