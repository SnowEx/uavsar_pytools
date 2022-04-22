import matplotlib.pyplot as plt
import os
from os.path import basename
import numpy as np
import logging

from uavsar_pytools.download.download import download_image, download_zip
from uavsar_pytools.convert.file_control import unzip
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert
from uavsar_pytools.UavsarImage import UavsarImage

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

class UavsarCollection():
    """
    Class to handle uavsar collections containing many different image pairs. Methods include downloading and converting images.

    Args:
        collection (str): name of collection. Found at: https://api.daac.asf.alaska.edu/services/utils/mission_list
        work_dir (str): directory to download images into
        overwrite (bool): Do you want to overwrite pre-existing files [Default = False]
        clean (bool): Do you want to erase binary files after completion [Default = False]
        debug (str): level of logging (not yet implemented)

    Attributes:
        zipped_fp (str): filepath to downloaded zip directory. Created automatically after downloading.
        binary_fps (str): filepaths of downloaded binary images. Created automatically after unzipping.
        ann_fp: file path to annotation file. Created automatically after unzipping.
        arr (array): processed numpy array of the image
        desc (dict): description of image from annotation file.
    """

    Scenes = []

    def __init__(self, collection, work_dir, overwrite = False, clean = False, debug = False):
        self.url = url
        self.work_dir = os.path.expanduser(work_dir)
        self.debug = debug
        self.clean = clean
        self.overwrite = overwrite

    def download(self):
        pass