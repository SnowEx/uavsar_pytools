import unittest

import numpy as np

from uavsar_pytools.polsar import (pol_from_fp, calc_C3, C3_to_T3, T3_to_H, T3_to_A,
                                   T3_to_alpha1, T3_to_mean_alpha, uavsar_H_A_alpha,
                                   vectorized_uavsar_H_A_alpha)


def _random_pixel(rng, n_looks=30):
    """Multilooked UAVSAR cross products and the true Pauli coherency matrix."""
    hh = rng.standard_normal(n_looks) + 1j * rng.standard_normal(n_looks)
    hv = 0.3 * (rng.standard_normal(n_looks) + 1j * rng.standard_normal(n_looks))
    vv = 0.8 * hh + 0.4 * (rng.standard_normal(n_looks) + 1j * rng.standard_normal(n_looks))
    products = (np.mean(hh * np.conj(hh)).real, np.mean(hh * np.conj(hv)),
                np.mean(hv * np.conj(hv)).real, np.mean(hv * np.conj(vv)),
                np.mean(hh * np.conj(vv)), np.mean(vv * np.conj(vv)).real)
    kp = np.stack([hh + vv, hh - vv, 2 * hv]) / np.sqrt(2)
    T3_true = (kp @ kp.conj().T) / n_looks
    return products, T3_true


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


class TestCoherency(unittest.TestCase):

    def setUp(self):
        self.rng = np.random.default_rng(0)
        self.products, self.T3_true = _random_pixel(self.rng)
        self.T3 = C3_to_T3(calc_C3(*self.products))

    def test_T3_matches_pauli(self):
        np.testing.assert_allclose(self.T3, self.T3_true, atol=1e-12)

    def test_T3_hermitian(self):
        np.testing.assert_allclose(self.T3, self.T3.conj().T, atol=1e-12)

    def test_products_match_direct_eigendecomposition(self):
        w, v = np.linalg.eigh(self.T3_true)
        w, v = w[::-1], v[:, ::-1]
        p = w / w.sum()
        alphas = np.arccos(np.abs(v[0, :]))
        self.assertAlmostEqual(T3_to_alpha1(self.T3), np.rad2deg(alphas[0]), places=6)
        self.assertAlmostEqual(T3_to_mean_alpha(self.T3), np.rad2deg(np.sum(p * alphas)), places=6)
        self.assertAlmostEqual(T3_to_H(self.T3), -np.sum(p * np.log(p) / np.log(3)), places=6)
        self.assertAlmostEqual(T3_to_A(self.T3), (w[1] - w[2]) / (w[1] + w[2]), places=6)

    def test_degenerate_eigenvalues_are_finite(self):
        # Pure odd bounce: HH = VV, HV = 0 gives T3 = diag(2, 0, 0)
        T3 = C3_to_T3(calc_C3(1.0, 0j, 0.0, 0j, 1.0 + 0j, 1.0))
        self.assertAlmostEqual(T3_to_alpha1(T3), 0.0)
        self.assertAlmostEqual(T3_to_mean_alpha(T3), 0.0)
        self.assertAlmostEqual(T3_to_H(T3), 0.0)
        self.assertAlmostEqual(T3_to_A(T3), 0.0)


class TestVectorized(unittest.TestCase):

    def test_vectorized_matches_per_pixel(self):
        rng = np.random.default_rng(1)
        rows, cols = 3, 4
        stack = np.empty((rows, cols, 6), dtype=np.complex128)
        for i in range(rows):
            for j in range(cols):
                stack[i, j] = _random_pixel(rng)[0]
        stack[1, 2] = np.nan
        loop = uavsar_H_A_alpha(stack)
        vec = vectorized_uavsar_H_A_alpha(stack)
        for a, b in zip(loop, vec):
            self.assertEqual(b.shape, (rows, cols))
            self.assertTrue(np.isnan(b[1, 2]))
            np.testing.assert_allclose(a, b, atol=1e-8, equal_nan=True)


if __name__ == '__main__':
    unittest.main()
