import requests
import unittest
from unittest import mock
import sys
from os.path import exists, join
import shutil
import tempfile

import uavsar_pytools

# appending a path
sys.path.append('/Users/zachkeskinen/Documents/uavsar_pytools/')

from uavsar_pytools import UavsarImage, uavsar_image

def connected_to_internet(url='http://www.google.com/', timeout=5):
    ## https://stackoverflow.com/questions/3764291/how-can-i-see-if-theres-an-available-and-active-network-connection-in-python
    try:
        _ = requests.head(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        pass
        # print("No internet connection available.")
    return False

class TestImage(unittest.TestCase):
    """
    The basic class that inherits unittest.TestCase
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        test_url = 'https://unzip.asf.alaska.edu/INTERFEROMETRY_GRD/UA/alamos_35915_20005-003_20008-000_0007d_s01_L090_01_int_grd.zip/alamos_35915_20005-003_20008-000_0007d_s01_L090HH_01.cor.grd'
        image = UavsarImage(work_dir= tmpdirname, url = test_url)  # instantiate the Class

        # test case function to check the Person.set_name function
        def test_image_init(self):
            # print("Start uavsar image test\n")
            """
            Any method which starts with ``test_`` will considered as a test case.
            Testing initilization of image class
            """
            self.assertIsNotNone(self.image.url)
            self.assertIsNotNone(self.image.work_dir)
            self.assertIsNotNone(self.image.debug)
            self.assertIsNotNone(self.image.clean)
        
        internet = connected_to_internet()

        @unittest.skipIf(internet == False, "No Internet Connection")
        def test_image_download(self):
            self.image.download()
            self.assertIsNotNone(self.image.binary_fp)
            self.assertIsNotNone(self.image.ann_fp)
            self.assertTrue(exists(self.image.ann_fp))
            self.assertTrue(exists(self.image.binary_fp))
    
    def test_convert(self):
        



if __name__ == '__main__':
    unittest.main()