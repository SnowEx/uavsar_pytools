"""Synthetic annotation and binary files through read_annotation and grd_tiff_convert."""
import os

import numpy as np
import pandas as pd
import rasterio as rio

from uavsar_pytools.convert.tiff_conversion import read_annotation, grd_tiff_convert

GRID = """{p}.set_rows (pixels) = 4 ; rows
{p}.set_cols (pixels) = 5 ; cols
{p}.row_mult (deg/pixel) = -0.0000555600 ; dlat
{p}.col_mult (deg/pixel) = 0.0000555600 ; dlon
{p}.row_addr (deg) = 39.0 ; lat
{p}.col_addr (deg) = -108.0 ; lon
{p}.val_size (bytes) = 4 ; size
{p}.val_frmt (&) = REAL*4 ; format
"""


def _write_ann(fp, prefixes, endian='LITTLE ENDIAN'):
    text = ''.join(GRID.format(p=p) for p in prefixes) + f'val_endi (&) = {endian} ; endian\n'
    with open(fp, 'w') as f:
        f.write(text)


def test_read_annotation_insar_times(tmp_path):
    fp = tmp_path / 'a.ann'
    lines = []
    for p in ['1', '2']:
        for t in ['start', 'stop']:
            lines.append(f'{t} time of acquisition for pass {p} (&) = 10-Feb-2021 12:00:00 UTC ; time')
    fp.write_text('\n'.join(lines) + '\n')
    desc = read_annotation(fp)
    assert isinstance(desc['start time of acquisition for pass 1']['value'], pd.Timestamp)


def test_hgt_keeps_zero(tmp_path):
    ann = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.ann'
    _write_ann(ann, ['hgt'])
    z = np.arange(20, dtype='float32').reshape(4, 5)
    z[0, 0] = 0.0
    z[1, 1] = -10000.0
    hgt = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.hgt'
    z.tofile(hgt)
    _, arr, _, out_fp = grd_tiff_convert(str(hgt), str(tmp_path), ann_fp=str(ann), overwrite=True)
    with rio.open(out_fp) as src:
        saved = src.read(1)
    assert saved[0, 0] == 0.0
    assert np.isnan(saved[1, 1])
    assert saved[3, 4] == 19.0


def test_inc_uses_hgt_grid(tmp_path):
    ann = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.ann'
    _write_ann(ann, ['hgt'])
    z = np.full((4, 5), 0.7, dtype='float32')
    inc = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.inc'
    z.tofile(inc)
    _, arr, _, out_fp = grd_tiff_convert(str(inc), str(tmp_path), ann_fp=str(ann), overwrite=True)
    assert os.path.exists(out_fp)
    np.testing.assert_allclose(arr, 0.7)


def test_slope_keeps_zero_and_splits_components(tmp_path):
    ann = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.ann'
    _write_ann(ann, ['slope'])
    east = np.zeros((4, 5), dtype='float32')
    north = np.full((4, 5), 0.25, dtype='float32')
    north[2, 2] = -10000.0
    inter = np.empty(40, dtype='float32')
    inter[::2] = east.ravel()
    inter[1::2] = north.ravel()
    slope = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.slope'
    inter.tofile(slope)
    _, _, _, fps = grd_tiff_convert(str(slope), str(tmp_path), ann_fp=str(ann), overwrite=True)
    with rio.open([f for f in fps if 'east' in f][0]) as src:
        assert np.all(src.read(1) == 0.0)
    with rio.open([f for f in fps if 'north' in f][0]) as src:
        n = src.read(1)
    assert np.isnan(n[2, 2])
    assert n[0, 0] == 0.25


def test_big_endian_annotation(tmp_path):
    ann = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.ann'
    _write_ann(ann, ['hgt'], endian='BIG ENDIAN')
    z = np.arange(1, 21, dtype='>f4').reshape(4, 5)
    hgt = tmp_path / 'site_27416_21011_003_210218_L090_CX_01.hgt'
    z.tofile(hgt)
    _, arr, _, _ = grd_tiff_convert(str(hgt), str(tmp_path), ann_fp=str(ann), overwrite=True)
    np.testing.assert_allclose(arr, np.arange(1, 21).reshape(4, 5))


def test_read_annotation_scientific_notation(tmp_path):
    ann = tmp_path / 'a.ann'
    ann.write_text('grd_pwr.row_mult (deg/pixel) = -5.556e-05 ; G\n'
                   'grd_pwr.set_rows (pixels) = 16418 ; G\n'
                   'grd_pwr.row_addr (deg) = 44.48811432 ; C\n'
                   'Flight ID for Pass 1 (&) = 21021 ; F\n'
                   'Processor Version (&) = v2.1.3 ; F\n')
    d = read_annotation(str(ann))
    assert d['grd_pwr.row_mult']['value'] == -5.556e-05
    assert d['grd_pwr.set_rows']['value'] == 16418
    assert d['grd_pwr.row_addr']['value'] == 44.48811432
    assert d['flight id for pass 1']['value'] == 21021
    assert d['processor version']['value'] == 'v2.1.3'
