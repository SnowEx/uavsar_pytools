"""
Group of Uavsar functions that are wrapped in classes for seperated use.
"""

import os
from os.path import exists, expanduser, join
from getpass import getpass
import logging

from uavsar_pytools.download.download import download_image, download_zip, stream_download
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert, read_annotation
from uavsar_pytools.convert.file_control import unzip

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

def create_netrc():
    username = input('Enter ASF or JPL username: ')
    password = getpass('Enter ASF or JPL password: ')
    home = expanduser("~")
    local = join(home, '.netrc')
    lines = ['machine urs.earthdata.nasa.gov', f'login {username}', f'password {password}']

    if not exists(local):
        with open(local, 'x') as f:
            f.writelines('\n'.join(lines))
    else:
        with open(local, 'a') as f:
            f.write('\n')
            f.writelines('\n'.join(lines))

    # os.chmod(local, 600)
