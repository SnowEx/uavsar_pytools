"""
File control functions for uavsar_pytools.
"""

from zipfile import ZipFile
from tqdm import tqdm
import os
from os.path import exists, join

import logging
log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

def unzip(dir_path, out_dir, pols = None):
    """
    Function to extract zipped directory with tqdm progress bar.
    From: https://stackoverflow.com/questions/4006970/monitor-zip-file-extraction-python.

    Args:
        dir_path (string) - path to zipped directory to unpack
        out_dir (string) - path to directory to extract files to.
    """
    assert exists(dir_path), f'Zipped directory at {dir_path} not found.'

    # Open your .zip file
    with ZipFile(file=dir_path) as zip_file:

        if pols:
            pol_list = [s for s in zip_file.namelist() if any(xs in s for xs in pols)]
            checked_list = [f for f in pol_list if not exists(join(out_dir, f))]
        else:
            pol_list = zip_file.namelist()
            checked_list = [f for f in pol_list if not exists(join(out_dir, f))]


        # Loop over each file
        if checked_list:
            for file in tqdm(iterable=checked_list, total=len(checked_list), unit = 'file', desc='Unzipping'):
                # Extract each file to another directory
                zip_file.extract(member=file, path=out_dir)
        else:
            log.info('No files found to unzip. Check if polarizations exist.')

    return [join(out_dir, fp) for fp in pol_list]