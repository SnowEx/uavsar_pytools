"""
Group of Uavsar functions that are wrapped in classes for seperated use.
"""

import os
from os.path import exists, expanduser, join
import logging
from netrc import netrc
from subprocess import Popen
from getpass import getpass

from uavsar_pytools.download.download import download_image, download_zip, stream_download
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert, read_annotation
from uavsar_pytools.convert.file_control import unzip

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

def create_netrc():
    """
    Creates netrc file for user. This is adapted to python 3.9 from: https://git.earthdata.nasa.gov/projects/LPDUR/repos/daac_data_download_python/browse/EarthdataLoginSetup.py
    """
    urs = 'urs.earthdata.nasa.gov'    # Earthdata URL to call for authentication
    prompts = ['Enter NASA Earthdata Login Username \n(or create an account at urs.earthdata.nasa.gov): ',
           'Enter NASA Earthdata Login Password: ']

    try:
        netrcDir = os.path.expanduser("~/.netrc")
        netrc(netrcDir).authenticators(urs)[0]

    # Below, create a netrc file and prompt user for NASA Earthdata Login Username and Password
    except FileNotFoundError:
        homeDir = os.path.expanduser("~")
        netrc_fp = join(homeDir,'.netrc')
        Popen(f'touch {netrc_fp} | chmod og-rw {netrc_fp} | echo machine {urs} >> {netrc_fp}', shell=True)
        Popen(f'echo login {getpass(prompt=prompts[0])} >> {netrc_fp}', shell=True)
        Popen(f'echo password {getpass(prompt=prompts[1])} >> {netrc_fp}', shell=True)

    # Determine OS and edit netrc file if it exists but is not set up for NASA Earthdata Login
    except TypeError:
        homeDir = os.path.expanduser("~")
        netrc_fp = join(homeDir,'.netrc')
        Popen(f'echo machine {urs} >> {netrc_fp}'.format(homeDir + os.sep, urs), shell=True)
        Popen(f'echo login {getpass(prompt=prompts[0])} >> {netrc_fp}', shell=True)
        Popen(f'echo password {getpass(prompt=prompts[1])} >> {netrc_fp}', shell=True)

    # If permission denied t
    except PermissionError:
        log.warning('Permission error. Change permissions on netrc file.')
