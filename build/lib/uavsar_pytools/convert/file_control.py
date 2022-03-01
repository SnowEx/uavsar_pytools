"""
File control functions for uavsar_pytools.
"""

from zipfile import ZipFile
from tqdm import tqdm
from os.path import exists, join

def unzip(dir_path, out_dir):
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

        checked_list = [f for f in zip_file.namelist() if not exists(join(out_dir, f))]
        # Loop over each file
        if checked_list:
            for file in tqdm(iterable=checked_list, total=len(zip_file.namelist()), unit = 'file', desc='Unzipping'):
                # Extract each file to another directory
                zip_file.extract(member=file, path=out_dir)

    return [join(out_dir, fp) for fp in zip_file.namelist()]