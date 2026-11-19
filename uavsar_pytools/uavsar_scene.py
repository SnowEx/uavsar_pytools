import matplotlib.pyplot as plt
import os
from os.path import basename, dirname, join
import numpy as np
import pandas as pd
import logging
import shutil
from glob import glob
from random import choice

from uavsar_pytools.download.download import download_zip, download_image
from uavsar_pytools.convert.file_control import unzip
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert
from uavsar_pytools.uavsar_image import UavsarImage

log = logging.getLogger(__name__)

class UavsarScene():
    """
    Class to handle uavsar zip directories. Methods include downloading and converting images.

    Args:
        url (str): ASF or JPL url to a zip uavsar directory
        work_dir (str): directory to download images into
        overwrite (bool): Do you want to overwrite pre-existing files [Default = False]
        clean (bool): Do you want to erase binary files after completion [Default = False]
        pols (list): Do you want only certain polarizations? [Default = all available]
        debug (str): level of logging (not yet implemented)

    Attributes:
        zipped_fp (str): filepath to downloaded zip directory. Created automatically after downloading.
        binary_fps (str): filepaths of downloaded binary images. Created automatically after unzipping.
        ann_fp: file path to annotation file. Created automatically after unzipping.
        arr (array): processed numpy array of the image
        desc (dict): description of image from annotation file.
    """

    def __init__(self, url, work_dir, clean = True, debug = False, pols = None, low_ram = False, scene_name = None):
        self.url = url
        # Zip scenes are named after the zip; file list scenes pass the ASF scene name
        self.pair_name = scene_name if scene_name else basename(url).split('.')[0]
        self.work_dir = os.path.expanduser(work_dir)
        self.clean = clean
        self.debug = debug
        self.low_ram = low_ram
        self.zipped_fp = None
        self.ann_fp = None
        self.binary_fps = []
        self.images = {}
        self.tmp_dir = None
        if pols:
            pols = [pol.upper() for pol in pols]
            if set(pols).issubset(['VV','VH','HV','HH']):
                self.pols = pols
            else:
                raise ValueError('Bad Polarization Provided.')
        else:
            self.pols = pols


    def download(self, sub_dir = 'tmp/', ann = True):
        """
        Download an uavsar image or zip file from a ASF or JPL url.
        Args:
            download_dir (str): directory to download image to. Will be created if it doesn't exists.
            ann (bool): download associated annotation file? [default = True]
        """
        out_dir = os.path.join(self.work_dir, sub_dir, self.pair_name)
        self.tmp_dir = out_dir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        if self.url.split('.')[-1] == 'zip':
            self.zipped_fp = download_zip(self.url, out_dir)
        else:
            log.warning('UavsarScene for zip files. Using UavsarImage for single images.')

    def download_files(self, urls, sub_dir = 'tmp/'):
        """
        Download a list of individual product files (the layout ASF serves UAVSAR in
        since 2026, one url per binary file plus the .ann) into this scene's temp dir.
        Args:
            urls (list): file urls for one scene, including the .ann
            sub_dir (str): sub-directory in working directory to download into
        """
        out_dir = os.path.join(self.work_dir, sub_dir, self.pair_name)
        self.tmp_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)
        self.binary_fps = []
        for url in urls:
            local, _ = download_image(url, out_dir, ann=False)
            self.binary_fps.append(local)

    def files_to_tiffs(self, urls):
        """Download a scene's individual files and convert them to WGS84 geotiffs."""
        self.download_files(urls)
        self.binary_to_tiffs()
        df = pd.DataFrame(choice(list(self.images.values()))['description'])
        df.to_csv(join(self.out_dir, self.pair_name + '.csv'))

    def unzip(self, in_dir = None, sub_dir = 'bin_imgs/'):
        """
        Unpack a zipped directory.
        Args:
            in_dir (str): directory to unzip frin
            sub_dir (str): sub-directory in working directory to unzip into
        """
        if not in_dir:
            if not self.zipped_fp:
                log.warning('No known zip file for this scene. Please provide.')
            else:
                in_dir = self.zipped_fp

        out_dir = os.path.join(self.tmp_dir, sub_dir)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        self.binary_fps = unzip(in_dir, out_dir, pols = self.pols)

    def binary_to_tiffs(self, binary_dir = None, ann_fp = None):
        """
        Convert a set of binary images to WGS84 geotiffs.
        Args:
            sub_dir (str): sub-directory in working directory to put tiffs
            binary_dir (str): directory containing binary files. Autogenerated from unzipping.
        """
        pols = ['VV','VH','HV','HH']
        if not binary_dir:
            if not self.binary_fps:
                raise Exception('No binary files or directory known')
            binary_dir = dirname(self.binary_fps[0])
        else:
            # Full paths, not bare file names, so conversion works from any cwd
            self.binary_fps = sorted(glob(join(binary_dir, '*')))

        out_dir = os.path.join(self.work_dir, self.pair_name)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        # Per polarization annotation files, only filled when no ann_fp is given
        ann_dic = {}
        if not ann_fp:
            ann_fps = [a for a in self.binary_fps if '.ann' in a]
            for pol in pols:
                ann_pol = [fp for fp in ann_fps if pol in fp]
                if ann_pol:
                    ann_dic[pol] = ann_pol[0]

            if not ann_fps:
                log.warning('No annotation file found for binary files.')

        binary_img_fps = [f for f in self.binary_fps if '.ann' not in f]

        for f in binary_img_fps:
            if len(ann_dic) > 0:
                f_pol = [pol for pol in pols if pol in basename(f)][0]
                ann_fp = ann_dic[f_pol]
            if not ann_fp:
                ann_fp = ann_fps[0]
            desc, array, type, out_fp = grd_tiff_convert(f, out_dir, ann_fp = ann_fp, overwrite = True, debug=self.debug)
            if self.low_ram:
                self.images[type] = {'description': desc, 'out_fp':out_fp, 'type':type}
            else:
                self.images[type] = {'description': desc, 'array':  array, 'out_fp':out_fp, 'type':type}
        self.out_dir = out_dir

        # Remove only this scene's download directory, never the shared parent
        if self.clean and self.tmp_dir and os.path.isdir(self.tmp_dir):
            shutil.rmtree(self.tmp_dir)

    def url_to_tiffs(self):
        self.download()
        self.unzip()
        self.binary_to_tiffs()
        df = pd.DataFrame(choice(list(self.images.values()))['description'])
        df.to_csv(join(self.out_dir, self.pair_name + '.csv'))


    def show(self, i):
        """
        Convenience function for checking a few images within the zip file for successful conversion.
        Likely types = ['unw','int','cor','hgt','slope','']
        """
        if i in self.images.keys():
            array = self.images[i]['array']
            if array.dtype == np.float64:
                vmin, vmax = np.nanquantile(array, [0.1,0.9])
                plt.imshow(array, vmin = vmin ,vmax = vmax)
            else:
                array = np.abs(array)
                vmin, vmax = np.nanquantile(array, [0.1,0.9])
                plt.imshow(array, vmin = vmin ,vmax = vmax)
            plt.title(self.images[i]['type'])
            plt.colorbar()
            plt.show()







