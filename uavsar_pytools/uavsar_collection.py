import os
from os.path import basename, join, expanduser
from glob import glob
import shutil
import logging
import asf_search as asf
import pandas as pd

from uavsar_pytools.uavsar_scene import UavsarScene
from uavsar_pytools.uavsar_image import UavsarImage

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
        pols (list): Do you want only certain polarizations? [Default = all available]
        dates (list): List of 1: start date and 2: end date to constrain collection results.
        low_ram (bool): decimates by a factor of 100 the arrays to conserve memory. [Default = True]
        inc (bool): download incidence angle as well? [Default = False]

    Methods:
        collection_to_tiffs(): Main method. Finds all Uavsar Images in the collection and downloads, converts them to GeoTiffs.
        find_urls() Finds all urls and returns thems as .results to the object. Each .result has a .properties property it inherits from asf_search.
    """

    def __init__(self, collection, work_dir, overwrite = False, clean = True, debug = False, pols = None, dates = None, low_ram = True, inc = False):
        self.collection = collection
        self.work_dir = expanduser(work_dir)
        self.overwrite = overwrite
        self.clean = clean
        self.debug = debug
        self.pols = pols
        self.low_ram = low_ram
        self.inc = inc
        if pols:
            pols = [pol.upper() for pol in pols]
            if set(pols).issubset(['VV','VH','HV','HH']):
                self.pols = pols
            else:
                raise ValueError('Bad Polarization Provided.')
        self.dates = dates
        if dates:
            # define search parameters for sierra flight line
            self.start_date = pd.to_datetime(dates[0])
            self.end_date = pd.to_datetime(dates[1])

    def find_urls(self):
        # search for data
        if self.dates:
            self.results = asf.search(platform = 'UAVSAR',
                        processingLevel = (['INTERFEROMETRY_GRD']),
                        campaign = self.collection,
                        start = self.start_date,
                        end = self.end_date)
        else:
            self.results = asf.search(platform = 'UAVSAR',
                        processingLevel = (['INTERFEROMETRY_GRD']),
                        campaign = self.collection)
        log.info(f'Found {len(self.results)} image pairs')

    def results_to_tiffs(self):
        for result in self.results:
            prop = result.properties
            url = prop['url']
            log.info(f'Starting on: {url}')
            scene = UavsarScene(url = url, work_dir= self.work_dir, pols = self.pols, clean = self.clean, low_ram=self.low_ram)
            scene.url_to_tiffs()
            d1 = scene.images[0]['description']['start time of acquisition for pass 1']['value']
            d2 = scene.images[0]['description']['start time of acquisition for pass 2']['value']
            if self.inc:
                inc_res = asf.search(platform = 'UAVSAR',
                        processingLevel = (['INC']),
                        campaign = self.collection,
                        # frame= int(prop['frameNumber']),
                        relativeOrbit= int(prop['pathNumber']),
                        start= prop['startTime'],
                        end = prop['stopTime'])[0]
                url_dir = join(self.work_dir, basename(url).split('.')[0])
                inc_img = UavsarImage(inc_res.properties['url'], join(self.work_dir, url_dir), clean = True)
                inc_img.url_to_tiff()
            print(f'Completed {d1} to {d2}')

    def collection_to_tiffs(self):
        self.find_urls()
        self.results_to_tiffs()
