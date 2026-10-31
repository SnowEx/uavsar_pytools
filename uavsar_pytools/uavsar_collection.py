import os
import re
from os.path import join, expanduser
import logging
import asf_search as asf
import pandas as pd

from uavsar_pytools.uavsar_scene import UavsarScene
from uavsar_pytools.campaigns import site_code

log = logging.getLogger(__name__)

# ASF processing levels for UAVSAR since the 2026 catalogue change, keyed by the
# names this class has always accepted as img_type
PROCESSING_LEVELS = {
    'INTERFEROMETRY_GRD': 'RPI',
    'RPI': 'RPI',
    'PROJECTED': 'POLSAR',
    'POLSAR': 'POLSAR',
}

class UavsarCollection():
    """
    Class to handle uavsar collections containing many different image pairs. Methods include downloading and converting images.

    ASF now serves UAVSAR as one granule per scene with a url for every file
    rather than a zip. This class finds the scenes by site code (the first field of
    the scene name, e.g. 'lowman') or by a geometry, downloads the ground projected
    files for the requested polarizations and converts them to GeoTiffs.

    Args:
        collection (str): campaign name from the SnowEx list (e.g. 'Lowman, CO') or the
            UAVSAR site code that starts the scene names (e.g. 'lowman'). Ignored if
            geometry is given.
        work_dir (str): directory to download images into
        img_type (str): 'INTERFEROMETRY_GRD' (alias 'RPI') for repeat pass interferometry
            or 'PROJECTED' (alias 'POLSAR') for polarimetric products. [Default = INTERFEROMETRY_GRD]
        clean (bool): Do you want to erase binary files after completion [Default = True]
        pols (list): Only certain polarizations, e.g. ['HH', 'HV']. For polsar products
            the six cross products whose halves are both in the list are kept. [Default = all]
        dates (list): List of 1: start date and 2: end date to constrain collection results.
        low_ram (bool): do not keep the converted arrays in memory. [Default = True]
        inc (bool): also download the .inc incidence angle file (polsar only). [Default = False]
        geometry (str): WKT geometry to search by instead of a site code, e.g. 'POINT(-115.6 44.1)'.

    Methods:
        collection_to_tiffs(): Main method. Finds all Uavsar scenes in the collection and downloads, converts them to GeoTiffs.
        find_urls() Finds all scenes and returns them as .results. Each .result has a .properties property it inherits from asf_search.
    """

    def __init__(self, collection = None, work_dir = '~', overwrite = False, clean = True, \
    debug = False, pols = None, dates = None, low_ram = True, inc = False, img_type = 'INTERFEROMETRY_GRD',
    geometry = None):
        assert collection or geometry, 'Provide a collection name, site code or geometry.'
        self.collection = collection
        self.site = site_code(collection) if collection else None
        self.geometry = geometry
        self.work_dir = expanduser(work_dir)
        self.overwrite = overwrite
        self.clean = clean
        self.debug = debug
        self.pols = pols
        self.low_ram = low_ram
        self.inc = inc
        if img_type not in PROCESSING_LEVELS:
            raise ValueError(f'img_type must be one of {list(PROCESSING_LEVELS)}')
        self.img_type = img_type
        self.level = PROCESSING_LEVELS[img_type]
        if pols:
            pols = [pol.upper() for pol in pols]
            if set(pols).issubset(['VV','VH','HV','HH']):
                self.pols = pols
            else:
                raise ValueError('Bad Polarization Provided.')
        self.dates = dates
        if dates:
            self.start_date = pd.to_datetime(dates[0])
            self.end_date = pd.to_datetime(dates[1])
        self.results = []

    def find_urls(self):
        """Search ASF for scenes of this site (or geometry), processing level and dates."""
        opts = dict(platform = 'UAVSAR', processingLevel = [self.level], maxResults = 5000)
        if self.geometry:
            opts['intersectsWith'] = self.geometry
        else:
            # Scene names start with the site code, and ASF supports a trailing wildcard
            opts['granule_list'] = [f'{self.site}_*']
        if self.dates:
            opts['start'] = self.start_date
            opts['end'] = self.end_date
        self.results = asf.search(**opts)
        log.info(f'Found {len(self.results)} scenes')

    def _keep_file(self, name):
        """Whether a file of a scene should be downloaded: ground projected products,
        the annotation file, optionally the incidence angle, filtered by polarization."""
        if name.endswith('.inc'):
            return self.inc
        if not (name.endswith('.grd') or name.endswith('.ann')):
            return False
        if not self.pols:
            return True
        # RPI scenes carry one identical .ann per polarization; keep only the requested ones
        match = re.search(r'L\d{3}([HV]{2,4})(?=[_.])', name)
        if not match:
            return True
        pol = match.group(1)
        # Two character field (RPI) must be requested; four character (polsar) needs both halves
        halves = [pol[:2], pol[2:]] if len(pol) == 4 else [pol]
        return all(h in self.pols for h in halves)

    def scene_urls(self, result):
        """File urls to download for one search result."""
        urls = []
        for entry in result.umm.get('RelatedUrls', []):
            if entry.get('Type') not in ('GET DATA', 'EXTENDED METADATA'):
                continue
            url = entry['URL']
            # Skip the s3:// duplicates ASF lists next to the https urls
            if not url.startswith('http'):
                continue
            if url not in urls and self._keep_file(url.split('/')[-1]):
                urls.append(url)
        return urls

    def results_to_tiffs(self):
        for result in self.results:
            prop = result.properties
            name = prop['sceneName']
            urls = self.scene_urls(result)
            log.info(f'Starting on {name}: {len(urls)} files')
            scene = UavsarScene(url = urls[0], work_dir = self.work_dir, pols = self.pols,
                                clean = self.clean, low_ram = self.low_ram, scene_name = name)
            scene.files_to_tiffs(urls)
            log.info(f"Completed {name} ({prop.get('startTime')} to {prop.get('stopTime')})")

    def collection_to_tiffs(self):
        self.find_urls()
        self.results_to_tiffs()
