import unittest

from uavsar_pytools.polsar import pol_from_fp

class TestPolFromFp(unittest.TestCase):
    """
    Polarizations must be found in file names regardless of how many
    underscore separated fields a product uses.
    """

    def test_grd(self):
        fp = 'grmesa_27416_20003_000_200206_L090HHVV_CX_01.grd'
        self.assertEqual(pol_from_fp(fp), 'HHVV')

    def test_grd_with_trailing_field(self):
        fp = 'evergl_15704_09044_000_090616_L090HHHH_CX_02_grd.grd'
        self.assertEqual(pol_from_fp(fp), 'HHHH')

    def test_tiff(self):
        fp = '/data/evergl_15704_09044_000_090616_L090HVVV_CX_02_grd.grd.tiff'
        self.assertEqual(pol_from_fp(fp), 'HVVV')

    def test_no_polarization(self):
        with self.assertRaises(AssertionError):
            pol_from_fp('evergl_15704_09044_000_090616_L090_CX_02.ann')

if __name__ == '__main__':
    unittest.main()
