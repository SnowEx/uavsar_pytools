import os
import requests
import unittest
from unittest import mock
import sys
from os.path import exists, join
import shutil
import tempfile

import uavsar_pytools

from uavsar_pytools import UavsarImage, uavsar_image

def connected_to_internet(url='http://www.google.com/', timeout=5):
    ## https://stackoverflow.com/questions/3764291/how-can-i-see-if-theres-an-available-and-active-network-connection-in-python
    try:
        _ = requests.head(url, timeout=timeout)
        return True
    except requests.RequestException:
        pass
        # print("No internet connection available.")
    return False

class TestImage(unittest.TestCase):
    """
    The basic class that inherits unittest.TestCase
    """
    with tempfile.TemporaryDirectory() as tmpdirname:
        test_url = 'https://cumulus.asf.earthdatacloud.nasa.gov/PRODUCTS/UAVSAR/UAVSAR_RPI/lowman_05208_21019-019_21021-007_0006d_s01_L090_01/lowman_05208_21019-019_21021-007_0006d_s01_L090HH_01.cor.grd'
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
        
        @unittest.skipUnless(os.environ.get('UAVSAR_NETWORK_TESTS'), 'Set UAVSAR_NETWORK_TESTS=1 to run download tests')
        def test_image_download(self):
            self.image.download()
            self.assertIsNotNone(self.image.binary_fp)
            self.assertIsNotNone(self.image.ann_fp)
            self.assertTrue(exists(self.image.ann_fp))
            self.assertTrue(exists(self.image.binary_fp))
    
    def test_convert(self):
        self.skipTest('Conversion test needs a downloaded binary image.')


if __name__ == '__main__':
    unittest.main()

def test_show_complex_array(tmp_path, monkeypatch):
    """show() plots magnitude for complex products instead of raising."""
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    shown = []
    monkeypatch.setattr(plt, 'show', lambda: shown.append(True))
    image = UavsarImage(work_dir=str(tmp_path), url='https://example.org/a_L090HH_01.int.grd')
    image.arr = np.exp(1j * np.linspace(0, 6, 16)).reshape(4, 4).astype(np.complex64)
    image.show()
    image.arr = None
    image.show()
    assert len(shown) == 1
    plt.close('all')
