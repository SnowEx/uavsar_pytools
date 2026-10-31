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
