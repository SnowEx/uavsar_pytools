"""Analytic regression tests for calc_inc_angle (GitHub issues #53, #54).

All cases use planes, where the local incidence angle is known exactly:
for a surface with gradient (zx, zy) and ground->sensor unit look vector
(le, ln, lu), LIA = arccos((-zx*le - zy*ln + lu) / sqrt(1 + zx^2 + zy^2)).
In particular, when the fall line lies in the radar look plane,
LIA = flat_incidence -/+ slope (facing/away).
"""
import unittest

import numpy as np

from uavsar_pytools.incidence_angle import calc_inc_angle

PIX, N = 5.0, 100            # 5 m pixels, 100x100 grid
EDGE = 2                     # np.gradient edge rows/cols excluded from checks


def look_vectors(theta_deg, az_deg, shape, slant_range=20000.0):
    """Sensor->ground look vector grids (E, N, U) for a given flat-ground
    incidence angle and ground->sensor azimuth (degrees from north)."""
    t, a = np.radians(theta_deg), np.radians(az_deg)
    le, ln, lu = np.sin(t) * np.sin(a), np.sin(t) * np.cos(a), np.cos(t)
    return tuple(np.full(shape, -c * slant_range) for c in (le, ln, lu))


def plane_dem(zx, zy):
    """North-up DEM of a plane with dz/dEast = zx and dz/dNorth = zy."""
    cols, rows = np.meshgrid(np.arange(N) * PIX, np.arange(N) * PIX)
    return zx * cols - zy * rows  # rows run SOUTH, so northing = -row distance


def interior(arr):
    return arr[EDGE:-EDGE, EDGE:-EDGE]


class TestCalcIncAngle(unittest.TestCase):

    def assert_uniform(self, inc, expected_deg, tol=1e-6):
        np.testing.assert_allclose(interior(inc), expected_deg, atol=tol)

    def test_flat_ground(self):
        """On flat ground LIA equals the flat-ground incidence angle."""
        dem = np.zeros((N, N))
        for theta in (30.0, 45.0, 60.0):
            e, n, u = look_vectors(theta, az_deg=142.0, shape=dem.shape)
            self.assert_uniform(calc_inc_angle(dem, e, n, u, PIX), theta)

    def test_slope_facing_radar(self):
        """A 20 deg slope dipping toward the sensor: LIA = 45 - 20 = 25 deg."""
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=(N, N))  # sensor due east
        dem = plane_dem(zx=-np.tan(np.radians(20.0)), zy=0.0)    # dips east
        self.assert_uniform(calc_inc_angle(dem, e, n, u, PIX), 25.0)

    def test_slope_facing_away(self):
        """A 20 deg slope dipping away from the sensor: LIA = 45 + 20 = 65 deg."""
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=(N, N))
        dem = plane_dem(zx=np.tan(np.radians(20.0)), zy=0.0)     # dips west
        self.assert_uniform(calc_inc_angle(dem, e, n, u, PIX), 65.0)

    def test_oblique_azimuth_general_plane(self):
        """General case: oblique look azimuth, slope in both axes, checked
        against the analytic arccos(l_hat . n_hat)."""
        theta, az = 52.0, 322.0                                   # UAVSAR-like geometry
        zx, zy = np.tan(np.radians(15.0)), -np.tan(np.radians(10.0))
        e, n, u = look_vectors(theta, az, shape=(N, N))
        t, a = np.radians(theta), np.radians(az)
        le, ln, lu = np.sin(t) * np.sin(a), np.sin(t) * np.cos(a), np.cos(t)
        expected = np.degrees(np.arccos(
            (-zx * le - zy * ln + lu) / np.sqrt(1 + zx**2 + zy**2)))
        inc = calc_inc_angle(plane_dem(zx, zy), e, n, u, PIX)
        self.assert_uniform(inc, expected)

    def test_magnitude_invariance(self):
        """Result must not depend on look-vector magnitude (unit vs slant range)."""
        dem = plane_dem(zx=np.tan(np.radians(25.0)), zy=np.tan(np.radians(5.0)))
        a = calc_inc_angle(dem, *look_vectors(60.0, 200.0, dem.shape, 1.0), PIX)
        b = calc_inc_angle(dem, *look_vectors(60.0, 200.0, dem.shape, 25000.0), PIX)
        np.testing.assert_allclose(interior(a), interior(b), atol=1e-9)

    def test_steep_facing_slope_stays_physical(self):
        """Steep slope facing the radar: previously the unnormalized normal
        pushed cos > 1 into the arccos_theta fold; now LIA is exact and >= 0."""
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=(N, N))
        dem = plane_dem(zx=-np.tan(np.radians(44.0)), zy=0.0)    # LIA = 1 deg
        self.assert_uniform(calc_inc_angle(dem, e, n, u, PIX), 1.0)


if __name__ == '__main__':
    unittest.main()


class TestInputHandling(unittest.TestCase):
    """Nodata, file inputs and pixel spacing."""

    def _write_tif(self, fp, arr, crs, res, nodata=None):
        import rasterio as rio
        from rasterio.transform import from_origin
        with rio.open(fp, 'w', driver='GTiff', height=arr.shape[0], width=arr.shape[1],
                      count=1, dtype='float32', crs=crs, nodata=nodata,
                      transform=from_origin(500000.0, 4500000.0, res, res)) as dst:
            dst.write(arr.astype('float32'), 1)

    def test_nodata_hole_is_nan(self):
        import os, tempfile
        dem = np.full((20, 20), 1000.0)
        dem[10, 10] = -9999.0
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=dem.shape)
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, 'dem.tif')
            self._write_tif(fp, dem, 'EPSG:32611', 5.0, nodata=-9999.0)
            inc = calc_inc_angle(fp, e, n, u)
        # The hole and its four gradient neighbours are NaN, everything else is flat ground
        for r, c in [(10, 10), (9, 10), (11, 10), (10, 9), (10, 11)]:
            self.assertTrue(np.isnan(inc[r, c]))
        rest = np.ones_like(inc, dtype=bool)
        rest[9:12, 9:12] = False
        np.testing.assert_allclose(inc[rest], 45.0, atol=1e-6)

    def test_spacing_from_file_not_argument(self):
        import os, tempfile
        from pathlib import Path
        zx = -np.tan(np.radians(20.0))
        dem = plane_dem(zx=zx, zy=0.0)
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=dem.shape)
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, 'dem.tif')
            self._write_tif(fp, dem, 'EPSG:32611', PIX)
            # A wrong pixel_size must be ignored for file inputs, and Path must work
            inc = calc_inc_angle(Path(fp), e, n, u, pixel_size=1.0)
        np.testing.assert_allclose(interior(inc), 25.0, atol=1e-4)

    def test_geographic_crs_rejected(self):
        import os, tempfile
        dem = np.zeros((N, N))
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=dem.shape)
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, 'dem.tif')
            self._write_tif(fp, dem, 'EPSG:4326', 0.00005556)
            with self.assertRaises(ValueError):
                calc_inc_angle(fp, e, n, u)

    def test_rectangular_pixels(self):
        row_spacing, col_spacing = 10.0, 5.0
        zx = -np.tan(np.radians(20.0))
        cols, rows = np.meshgrid(np.arange(N) * col_spacing, np.arange(N) * row_spacing)
        dem = zx * cols
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=dem.shape)
        inc = calc_inc_angle(dem, e, n, u, pixel_size=(row_spacing, col_spacing))
        np.testing.assert_allclose(interior(inc), 25.0, atol=1e-6)

    def test_file_lkv_shape_mismatch_raises(self):
        import os, tempfile
        dem = np.zeros((N, N))
        e, n, u = look_vectors(45.0, az_deg=90.0, shape=(N, N + 1))
        with tempfile.TemporaryDirectory() as d:
            fp = os.path.join(d, 'e.tif')
            self._write_tif(fp, e, 'EPSG:32611', PIX)
            with self.assertRaises(AssertionError):
                calc_inc_angle(dem, fp, n, u, PIX)
