"""UavsarCollection against the per-file ASF layout, with search, download and conversion stubbed."""
import os

import numpy as np

from uavsar_pytools import uavsar_collection, uavsar_scene
from uavsar_pytools.uavsar_collection import UavsarCollection

BASE = 'https://cumulus.asf.earthdatacloud.nasa.gov/PRODUCTS/UAVSAR/UAVSAR_RPI/scene/'
STEM = 'lowman_05208_21019-019_21021-007_0006d_s01_L090'


class _Result:
    properties = {'sceneName': STEM + '_01', 'startTime': '2021-03-16T18:09:32Z', 'stopTime': '2021-03-22T17:07:49Z'}
    umm = {'RelatedUrls': (
        [{'Type': 'GET DATA', 'URL': BASE + f'{STEM}{p}_01{e}'} for p in ['HH', 'HV'] for e in ['.cor', '.cor.grd', '.unw.grd', '.hgt.grd']]
        + [{'Type': 'GET DATA', 'URL': BASE + f'{STEM}HH_01.amp1.kmz'},
           {'Type': 'EXTENDED METADATA', 'URL': BASE + f'{STEM}HH_01.ann'},
           {'Type': 'EXTENDED METADATA', 'URL': 's3://asf-cumulus-prod-products/' + f'{STEM}HH_01.ann'},
           {'Type': 'EXTENDED METADATA', 'URL': BASE + f'{STEM}HV_01.ann'}])}


def test_file_selection_rpi():
    col = UavsarCollection('Lowman, CO', pols=['HH'])
    names = [u.split('/')[-1] for u in col.scene_urls(_Result())]
    assert names == [f'{STEM}HH_01.cor.grd', f'{STEM}HH_01.unw.grd', f'{STEM}HH_01.hgt.grd', f'{STEM}HH_01.ann']


def test_file_selection_polsar_pols():
    col = UavsarCollection('lowman', img_type='PROJECTED', pols=['HH', 'HV'])
    keep = [p for p in ['HHHH', 'HHHV', 'HHVV', 'HVHV', 'HVVV', 'VVVV'] if col._keep_file(f'x_L090{p}_CX_01.grd')]
    assert keep == ['HHHH', 'HHHV', 'HVHV']
    assert col.level == 'POLSAR'
    assert not col._keep_file('x_L090_CX_01.inc')
    assert UavsarCollection('lowman', img_type='PROJECTED', inc=True)._keep_file('x_L090_CX_01.inc')


def test_search_options(monkeypatch):
    seen = {}
    monkeypatch.setattr(uavsar_collection.asf, 'search', lambda **kw: seen.update(kw) or [])
    UavsarCollection('Lowman, CO', dates=('2021-01-01', '2021-04-01')).find_urls()
    assert seen['granule_list'] == ['lowman_*']
    assert seen['processingLevel'] == ['RPI']
    assert str(seen['start'])[:10] == '2021-01-01'
    UavsarCollection(geometry='POINT(-115.6 44.1)').find_urls()
    assert seen['intersectsWith'] == 'POINT(-115.6 44.1)'


def test_results_to_tiffs(tmp_path, monkeypatch):
    downloaded, converted = [], []

    def fake_download(url, out_dir, ann=False, ann_url=None):
        fp = os.path.join(out_dir, url.split('/')[-1])
        open(fp, 'w').close()
        downloaded.append(fp)
        return fp, None

    def fake_convert(f, out_dir, ann_fp=None, overwrite=True, debug=False):
        converted.append((os.path.basename(f), os.path.basename(ann_fp)))
        return {'a': {'value': 1}}, np.zeros(2), os.path.basename(f).split('.')[-2], os.path.join(out_dir, 'o.tiff')

    monkeypatch.setattr(uavsar_scene, 'download_image', fake_download)
    monkeypatch.setattr(uavsar_scene, 'grd_tiff_convert', fake_convert)
    col = UavsarCollection('lowman', work_dir=str(tmp_path), pols=['HH'])
    col.results = [_Result()]
    col.results_to_tiffs()
    assert len(downloaded) == 4
    assert sorted(c[0].split('.')[-2] for c in converted) == ['cor', 'hgt', 'unw']
    assert all(c[1] == f'{STEM}HH_01.ann' for c in converted)
    out_dir = tmp_path / (STEM + '_01')
    assert (out_dir / (STEM + '_01.csv')).exists()
    assert not (tmp_path / 'tmp' / (STEM + '_01')).exists()   # cleaned


def test_collection_to_tiffs_searches_then_converts(monkeypatch):
    col = UavsarCollection('Lowman, CO', pols=['HH'])
    calls = []
    monkeypatch.setattr(col, 'find_urls', lambda: calls.append('find_urls'))
    monkeypatch.setattr(col, 'results_to_tiffs', lambda: calls.append('results_to_tiffs'))
    col.collection_to_tiffs()
    assert calls == ['find_urls', 'results_to_tiffs']


def test_end_date_covers_whole_day():
    import pandas as pd
    col = UavsarCollection('lowman', dates=('2021-03-22', '2021-03-22'))
    assert col.start_date == pd.Timestamp('2021-03-22')
    assert col.end_date == pd.Timestamp('2021-03-22 23:59:59')
    # An explicit time is kept as given
    col = UavsarCollection('lowman', dates=('2021-03-22', '2021-03-22 12:00'))
    assert col.end_date == pd.Timestamp('2021-03-22 12:00')
