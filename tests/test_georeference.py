"""georeference helpers. Skipped when GDAL python bindings are not installed."""
import os
import numpy as np
import pytest

pytest.importorskip('osgeo')

from uavsar_pytools.georeference import _segment_and_factor, combo_llhs  # noqa: E402


def test_segment_and_factor():
    assert _segment_and_factor('lowman_05208_01_BC_s2_2x8.llh') == ('2', '2x8')
    assert _segment_and_factor('/x/lowman_05208_21006_003_210210_L090HH_01_BC_s1_1x1.slc') == ('1', '1x1')


def test_combo_llhs_little_endian_in_segment_order(tmp_path):
    seg1 = np.array([1.0, 2.0, 3.0], dtype='<f')
    seg2 = np.array([4.0, 5.0, 6.0], dtype='<f')
    seg10 = np.array([7.0, 8.0, 9.0], dtype='<f')
    seg1.tofile(tmp_path / 'site_01_BC_s1_2x8.llh')
    seg10.tofile(tmp_path / 'site_01_BC_s10_2x8.llh')
    seg2.tofile(tmp_path / 'site_01_BC_s2_2x8.llh')
    out = combo_llhs(tmp_path)
    assert out == tmp_path / 'full.llh'
    np.testing.assert_array_equal(np.fromfile(out, '<f'), np.arange(1, 10, dtype='<f'))


def _synthetic_stack(d, nrows=60, ncols=80, fill_rows=5):
    """Synthetic 2x8 segment 1 stack: .llh, .lkv and .ann with a known geometry.
    Returns paths and the lat/lon arrays. The first rows are zero fill as in JPL files."""
    rows, cols = np.mgrid[0:nrows, 0:ncols]
    lat = 44.0 + 0.0005 * rows + 0.0002 * cols
    lon = -115.6 + 0.001 * cols - 0.0003 * rows
    hgt = np.full((nrows, ncols), 1500.0)
    lat[:fill_rows] = 0.0
    lon[:fill_rows] = 0.0
    llh = np.empty(nrows * ncols * 3, dtype='<f')
    llh[0::3], llh[1::3], llh[2::3] = lat.ravel(), lon.ravel(), hgt.ravel()
    llh_fp = d / 'site_05208_01_BC_s1_2x8.llh'
    llh.tofile(llh_fp)
    # Look vector components encode the slant pixel position so the mapping can be checked
    east, north, up = cols / ncols, rows / nrows, np.full((nrows, ncols), -1.0)
    lkv = np.empty(nrows * ncols * 3, dtype='<f')
    lkv[0::3], lkv[1::3], lkv[2::3] = east.ravel(), north.ravel(), up.ravel()
    lkv_fp = d / 'site_05208_01_BC_s1_2x8.lkv'
    lkv.tofile(lkv_fp)
    ann_fp = d / 'site_05208_21006_003_210210_L090HH_01_BC.ann'
    ann_fp.write_text(f'llh_1_2x8.set_rows (pixels) = {nrows} ; rows\n'
                      f'llh_1_2x8.set_cols (pixels) = {ncols} ; cols\n'
                      f'lkv_1_2x8 rows (pixels) = {nrows} ; rows\n'
                      f'lkv_1_2x8 columns (pixels) = {ncols} ; cols\n')
    return llh_fp, lkv_fp, ann_fp, lat, lon


def test_geolocate_lkv_synthetic(tmp_path):
    import rasterio as rio
    from uavsar_pytools.georeference import geolocate_uavsar
    llh_fp, lkv_fp, ann_fp, lat, lon = _synthetic_stack(tmp_path)
    out_dir = tmp_path / 'out'
    outs = geolocate_uavsar(str(lkv_fp), str(ann_fp), str(out_dir), str(llh_fp))
    names = sorted(os.path.basename(o) for o in outs)
    assert names == [f'site_05208_01_BC_s1_2x8.lkv.{c}.tif' for c in ['x', 'y', 'z']]
    valid = lat != 0
    with rio.open([o for o in outs if '.lkv.x.' in o][0]) as src:
        assert src.crs.to_epsg() == 4326
        # Output extent follows the valid lat/lon, not the zero fill
        assert abs(src.bounds.bottom - lat[valid].min()) < 0.001
        assert abs(src.bounds.top - lat[valid].max()) < 0.001
        assert abs(src.bounds.left - lon[valid].min()) < 0.001
        assert abs(src.bounds.right - lon[valid].max()) < 0.001
        # Slant pixel (30, 40) carries east = 40/80; find it at its own lat/lon
        r, c = src.index(lon[30, 40], lat[30, 40])
        assert abs(src.read(1)[r, c] - 40 / 80) < 0.02
    with rio.open([o for o in outs if '.lkv.y.' in o][0]) as src:
        r, c = src.index(lon[30, 40], lat[30, 40])
        assert abs(src.read(1)[r, c] - 30 / 60) < 0.02
    # Temp directory is gone and nothing else was left in out_dir
    assert sorted(os.listdir(out_dir)) == names


def test_geolocate_rejects_segment_mismatch(tmp_path):
    from uavsar_pytools.georeference import geolocate_uavsar
    llh_fp, lkv_fp, ann_fp, _, _ = _synthetic_stack(tmp_path)
    seg2 = tmp_path / 'site_05208_01_BC_s2_2x8.lkv'
    seg2.write_bytes(lkv_fp.read_bytes())
    with pytest.raises(ValueError):
        geolocate_uavsar(str(seg2), str(ann_fp), str(tmp_path / 'out2'), str(llh_fp))


def test_reproject_clip_mask(tmp_path):
    """A UTM raster whose value equals its easting is reprojected onto a lat/lon grid;
    the output takes the target grid and nodata mask and keeps the easting values."""
    import rasterio
    from rasterio.transform import from_origin
    from pyproj import Transformer
    from uavsar_pytools.georeference import reproject_clip_mask

    # Source: 10 m UTM 11N raster, value = easting of the pixel centre
    src_tr = from_origin(500000, 4870000, 10, 10)
    cols = np.arange(200)
    src = np.broadcast_to(500000 + 10 * (cols + 0.5), (200, 200)).astype('float32')
    src_fp = tmp_path / 'src.tif'
    with rasterio.open(src_fp, 'w', driver='GTiff', height=200, width=200, count=1,
                       dtype='float32', crs='EPSG:32611', transform=src_tr) as ds:
        ds.write(src, 1)

    # Target: coarser lat/lon grid inside the source footprint with a NaN hole
    match_tr = from_origin(-116.995, 43.973, 0.0002, 0.0002)
    match = np.ones((20, 20), dtype='float32')
    match[5:10, 5:10] = np.nan
    match_fp = tmp_path / 'match.tif'
    with rasterio.open(match_fp, 'w', driver='GTiff', height=20, width=20, count=1,
                       dtype='float32', crs='EPSG:4326', transform=match_tr, nodata=np.nan) as ds:
        ds.write(match, 1)

    out_fp = reproject_clip_mask(str(src_fp), str(match_fp), str(tmp_path / 'out.tif'))
    with rasterio.open(out_fp) as ds:
        out = ds.read(1)
        assert ds.crs.to_epsg() == 4326
        assert ds.transform.almost_equals(match_tr)
    assert out.shape == (20, 20)
    assert np.all(np.isnan(out[5:10, 5:10]))
    # Remaining pixels hold the easting of their own centre, within one source pixel
    rows, cols = np.mgrid[0:20, 0:20]
    lon = match_tr.c + (cols + 0.5) * match_tr.a
    lat = match_tr.f + (rows + 0.5) * match_tr.e
    east, _ = Transformer.from_crs('EPSG:4326', 'EPSG:32611', always_xy=True).transform(lon, lat)
    valid = ~np.isnan(out)
    assert valid.sum() == 400 - 25
    np.testing.assert_allclose(out[valid], east[valid], atol=10)
