"""
File control functions for uavsar_pytools.
"""

from zipfile import ZipFile
from tqdm import tqdm
from os import makedirs, isdir

def unzip(dir_path, out_dir):
    """
    Function to extract zipped directory with tqdm progress bar.
    From: https://stackoverflow.com/questions/4006970/monitor-zip-file-extraction-python.

    Args:
        dir_path (string) - path to zipped directory to unpack
        out_dir (string) - path to directory to extract files to.
    """
    assert isdir(dir_path), f'Zipped directory at {dir_path} not found.'
    makedirs(out_dir, exist_ok= True)

    # Open your .zip file
    with ZipFile(file=dir_path) as zip_file:

        # Loop over each file
        for file in tqdm(iterable=zip_file.namelist(), total=len(zip_file.namelist())):

            # Extract each file to another directory
            # If you want to extract to current working directory, don't specify path
            zip_file.extract(member=file, path=out_dir)