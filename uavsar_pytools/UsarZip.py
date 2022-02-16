import matplotlib.pyplot as plt
import os
import numpy as np
import logging

from uavsar_pytools.download.download import download_image, download_zip
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert
from uavsar_pytools.UavsarImg import UavsarImg

logging.basicConfig()

class UsarZip():
    """
    Class to handle uavsar zip directories. Methods include downloading and converting images.

    Args:
        url (str) - ASF or JPL url to a zip uavsar directory
        work_dir (str) = directory to download images into
        overwrite (bool) = Do you want to overwrite pre-existing files [Default = False]
        debug (str) = level of logging (not yet implemented)

    Attributes:
        binary_fp (str): filepath of downloaded images. Created automatically after downloading.
        ann_fp = file path to annotation file. Created automatically after downloading.
        arr (array) = processed numpy array of the image
        desc (dict) = description of image from annotation file.
    """

    def __init__(self, url, work_dir, debug = False):
        self.url = url
        self.work_dir = work_dir
        self.debug = debug


    def download(self, sub_dir = 'bin_imgs/'):
        """
        Download an uavsar image from a ASF or JPL url.
        Args:
            download_dir (str): directory to download image to. Will be created if it doesn't exists.
        """
        out_dir = os.path.join(self.work_dir,sub_dir)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        self.binary_fp, self.ann_fp = download_zip(self.url, out_dir)