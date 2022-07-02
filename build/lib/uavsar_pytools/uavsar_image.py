import matplotlib.pyplot as plt
import os
import numpy as np
import shutil
import logging

from uavsar_pytools.download.download import download_image
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert

logging.basicConfig()

class UavsarImage():
    """
    Class to handle individual uavsar images. Methods include downloading and converting images.

    Args:
        url (str) - ASF or JPL url to a single uavsar image
        work_dir (str) = directory to download images into
        overwrite (bool) = Do you want to overwrite pre-existing files [Default = False]
        debug (str) = level of logging (not yet implemented)
        ann_url (str) = optional parameter to manually provide annotation url associated with the file.
        clean (bool) = erase binary image  and annotation files? [Default = False]

    Attributes:
        binary_fp (str): filepath of downloaded images. Created automatically after downloading.
        ann_fp = file path to annotation file. Created automatically after downloading.
        arr (array) = processed numpy array of the image
        desc (dict) = description of image from annotation file.
    """

    def __init__(self, url, work_dir, ann_url = None, debug = False, clean = False):
        self.url = url
        self.work_dir = os.path.expanduser(work_dir)
        self.debug = debug
        self.binary_fp = None
        self.clean = clean
        self.ann_fp = None
        self.tiff_dir = None
        self.arr = None
        self.desc = None
        self.type = None

    def download(self, sub_dir = 'bin_imgs/', ann = True):
        """
        Download an uavsar image from a ASF or JPL url.
        Args:
            download_dir (str): directory to download image to. Will be created if it doesn't exists.
            ann (bool): download associated annotation file? [default = True]
        """
        out_dir = os.path.join(self.work_dir,sub_dir)
        self.bin_dir = out_dir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        self.binary_fp, self.ann_fp = download_image(self.url, output_dir= out_dir, ann = ann)

    def convert_to_tiff(self, binary_fp = None, sub_dir = None, ann_fp = None, overwrite = True):
        """
        Converts a binary image file with an associated annotation file to WGS84 geotiff.
        Args:
            binary_fp (str): path to input binary file
            out_dir (str): directory to save geotiff in
            ann_fp (str): path to UAVSAR annotation file
            overwrite (bool): overwrite exisiting file [default = False]
        Returns:
            self.arr: array of image values
            self.desc: description of image file from annotation
            self.type: type of file from binary file path
        """
        if sub_dir:
            out_dir = os.path.join(self.work_dir, sub_dir)
        else:
            out_dir = self.work_dir

        if not binary_fp:
            binary_fp = self.binary_fp

        if not ann_fp:
            ann_fp = self.ann_fp

        result = grd_tiff_convert(in_fp = binary_fp, out_dir = out_dir, ann_fp = ann_fp, overwrite = overwrite)
        if len(result) == 3:
            self.desc, self.arr, self.type = result

        if self.clean:
            shutil.rmtree(self.bin_dir)

    def show(self):
        """Convenience function to check converted array."""
        if self.arr != None:
            if len(self.arr.dtype) == 1:
                d = self.arr['real']
            else:
                d = (self.arr['real']**2 + self.arr['imaginary']**2)**0.5
            std_low = np.nanmedian(d) - np.nanstd(d)
            std_high = np.nanmedian(d) + np.nanstd(d)
            plt.imshow(d, vmin = std_low ,vmax = std_high)
            plt.title(os.path.basename(self.url))
            plt.colorbar()
            plt.show()


    def url_to_tiff(self, down_dir = 'bin_imgs/'):
        """Download binary file from url and convert to WGS84 geotiff."""
        self.download(sub_dir = down_dir)
        if self.ann_fp:
            self.convert_to_tiff()