"""
Group of Uavsar functions that are wrapped in classes for seperated use.
"""

import os
from os.path import exists, expanduser, join
import logging
from netrc import netrc
from getpass import getpass

from uavsar_pytools.download.download import download_image, download_zip, stream_download
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert, read_annotation
from uavsar_pytools.convert.file_control import unzip

log = logging.getLogger(__name__)

def create_netrc(urs = 'urs.earthdata.nasa.gov'):
    """
    Creates netrc file for user. This is adapted to python 3.9 from: https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse/EarthdataLoginSetup.py
    """
    prompts = ['Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ',
           'Enter NASA Earthdata Login Password: ']

    netrc_fp = join(expanduser("~"), '.netrc')

    try:
        netrc(netrc_fp).authenticators(urs)[0]
        return

    # No netrc file, or one without an entry for this host: append an entry below
    except (FileNotFoundError, TypeError):
        pass

    # If permission denied t
    except PermissionError:
        log.warning('Permission error. Change permissions on netrc file.')
        return

    username = getpass(prompt=prompts[0])
    password = getpass(prompt=prompts[1])

    # Write from Python so the password never appears on a shell command line
    # and the file is created owner-readable only.
    fd = os.open(netrc_fp, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a') as f:
        f.write(f'machine {urs}\nlogin {username}\npassword {password}\n')
    os.chmod(netrc_fp, 0o600)
