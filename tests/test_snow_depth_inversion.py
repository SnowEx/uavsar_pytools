"""Tests for snow_depth_inversion with scalar and array inputs."""
import numpy as np
import pytest

from uavsar_pytools.snow_depth_inversion import depth_from_phase, phase_from_depth


def test_hand_value():
    # -lambda * dphi / (4 pi (cos th - sqrt(eps - sin^2 th))) for dphi = 1, 40 deg, eps = 1.5
    dz = depth_from_phase(np.array([1.0]), np.radians(40.0), permittivity=1.5)
    np.testing.assert_allclose(dz, 0.068622, rtol=1e-4)


def test_array_permittivity():
    dz = depth_from_phase(np.ones((3, 3)), 0.7, permittivity=np.full((3, 3), 1.5))
    assert dz.shape == (3, 3)
    assert np.all(np.isfinite(dz))


def test_array_density():
    dz = depth_from_phase(np.ones((3, 3)), np.full((3, 3), 0.7), density=np.full((3, 3), 300.0))
    assert np.all(np.isfinite(dz))
    dphi = phase_from_depth(dz, np.full((3, 3), 0.7), density=np.full((3, 3), 300.0))
    np.testing.assert_allclose(dphi, 1.0)


def test_round_trip_scalar_density():
    phase = np.linspace(-3, 3, 7)
    dz = depth_from_phase(phase, 0.6, density=250.0)
    np.testing.assert_allclose(phase_from_depth(dz, 0.6, density=250.0), phase)


def test_requires_permittivity_or_density():
    with pytest.raises(ValueError):
        depth_from_phase(np.ones(3), 0.6)


def test_swe_oveisgharan_hand_value():
    from uavsar_pytools.snow_depth_inversion import swe_from_phase_oveisgharan
    # phase / (-2 k (-0.6784 th^2 + 0.2899 th - 0.8473)), th = 40 deg, lambda = 0.0555 m
    th = np.radians(40.0)
    expected = 1.0 / (-2 * 2 * np.pi / 0.0555 * (-0.6784 * th**2 + 0.2899 * th - 0.8473))
    np.testing.assert_allclose(swe_from_phase_oveisgharan(np.array([1.0]), th), expected)
    # Degrees are detected and give the same answer as radians
    np.testing.assert_allclose(swe_from_phase_oveisgharan(np.array([1.0]), 40.0), expected)


def test_swe_leinss_hand_value():
    from uavsar_pytools.snow_depth_inversion import swe_from_phase_leinss
    # phase / (k alpha (1.59 + th^2.5)), th = 40 deg, L band wavelength
    th = np.radians(40.0)
    expected = 1.0 / (2 * np.pi / 0.238403545 * (1.59 + th**2.5))
    np.testing.assert_allclose(swe_from_phase_leinss(np.array([1.0]), th), expected)
    np.testing.assert_allclose(swe_from_phase_leinss(np.array([1.0]), 40.0), expected)
    np.testing.assert_allclose(swe_from_phase_leinss(np.array([1.0]), th, alpha=2.0), expected / 2)


def test_swe_array_inputs():
    from uavsar_pytools.snow_depth_inversion import swe_from_phase_leinss, swe_from_phase_oveisgharan
    phase = np.linspace(-3, 3, 9).reshape(3, 3)
    inc = np.full((3, 3), 35.0)
    for f in (swe_from_phase_leinss, swe_from_phase_oveisgharan):
        swe = f(phase, inc)
        assert swe.shape == (3, 3)
        assert np.all(np.isfinite(swe))
        # SWE is linear in phase
        np.testing.assert_allclose(f(2 * phase, inc), 2 * swe)
