"""Offline tests of download helpers. Network calls are stubbed."""
import os

import pytest

from uavsar_pytools.download import download, download_slcs


def _fake_stream_download(url, output_f):
    with open(output_f, 'wb') as f:
        f.write(b'x')


def test_download_image_without_ann_returns_tuple(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'stream_download', _fake_stream_download)
    url = 'https://example.org/alamos_35915_L090HH_01.cor.grd'
    local, ann = download.download_image(url, str(tmp_path), ann=False)
    assert local == os.path.join(str(tmp_path), 'alamos_35915_L090HH_01.cor.grd')
    assert ann is None
    assert os.path.exists(local)


def test_download_image_with_ann_url(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'stream_download', _fake_stream_download)
    url = 'https://example.org/alamos_35915_L090HH_01.cor.grd'
    local, ann = download.download_image(url, str(tmp_path), ann_url='https://example.org/a.ann')
    assert ann == os.path.join(str(tmp_path), 'a.ann')
    assert os.path.exists(ann)


BASE = download_slcs.JPL_BASE_URL


class _Granule:
    def __init__(self, name):
        self.properties = {'sceneName': name}


def _probe_found_in(release, tag):
    """Probe stub: only urls under the given release and tag exist."""
    return lambda url: 'file' if f'/{release}/' in url and f'_{tag}' in url.split('/')[-1] else 'missing'


def test_get_uavsar_slcs_search_and_urls(monkeypatch):
    seen = {}

    def fake_search(**kw):
        seen.update(kw)
        return [_Granule('lowman_05208_21021_007_210322_L090_CX_01'),
                _Granule('UA_lowman_23205_21021_006_210322_L090_CX_01')]

    monkeypatch.setattr(download_slcs.asf, 'search', fake_search)
    monkeypatch.setattr(download_slcs, '_probe', _probe_found_in('Release30', 'BC'))
    links = download_slcs.get_uavsar_slcs('Lowman, CO', getann=True, getllh=True, getlkv=True, getdop=True,
                                          seg=['s1'], pxlsp=['2x8'])
    # ASF search by site wildcard and processing level, not campaign or beam mode
    assert seen['processingLevel'] == ['POLSAR']
    assert seen['granule_list'] == ['lowman_*']
    assert 'campaign' not in seen and 'beamMode' not in seen
    # Both scene name forms (with and without the old UA_ prefix) resolve to flight lines
    assert sorted(links) == ['lowman_05208', 'lowman_23205']
    folder = f'{BASE}/Release30/lowman_05208_01'
    assert links['lowman_05208'] == [
        f'{folder}/lowman_05208_21021_007_210322_L090HH_01_BC_s1_2x8.slc',
        f'{folder}/lowman_05208_01_BC_s1_2x8.llh',
        f'{folder}/lowman_05208_01_BC_s1_2x8.lkv',
        f'{folder}/lowman_05208_21021_007_210322_L090HH_01_BC.ann',
        f'{folder}/lowman_05208_01_BC.dop']


def test_get_uavsar_slcs_flight_num_and_version(monkeypatch):
    monkeypatch.setattr(download_slcs.asf, 'search', lambda **k: [
        _Granule('lowman_05208_21021_007_210322_L090_CX_01'),
        _Granule('lowman_23205_21021_006_210322_L090_CX_01')])
    monkeypatch.setattr(download_slcs, '_probe', _probe_found_in('Release21', 'BU'))
    links = download_slcs.get_uavsar_slcs('lowman', flight_num='23205', version=2, seg=['s2'])
    assert list(links) == ['lowman_23205']
    assert links['lowman_23205'] == [
        f'{BASE}/Release21/lowman_23205_02/lowman_23205_21021_006_210322_L090HH_02_BU_s2_2x8.slc']


def test_get_uavsar_slcs_missing_version_raises(monkeypatch):
    monkeypatch.setattr(download_slcs.asf, 'search', lambda **k: [_Granule('lowman_05208_21021_007_210322_L090_CX_01')])
    monkeypatch.setattr(download_slcs, '_probe', lambda url: 'missing')
    with pytest.raises(ValueError, match='version 3'):
        download_slcs.get_uavsar_slcs('lowman', version=3)


def test_get_uavsar_slcs_host_down(monkeypatch):
    monkeypatch.setattr(download_slcs.asf, 'search', lambda **k: [_Granule('lowman_05208_21021_007_210322_L090_CX_01')])

    def refused(*a, **k):
        raise download_slcs.requests.ConnectionError('refused')

    monkeypatch.setattr(download_slcs.requests, 'head', refused)
    with pytest.raises(ConnectionError, match='not answering'):
        download_slcs.get_uavsar_slcs('lowman')


def test_probe_html_page_is_missing(monkeypatch):
    class R:
        def __init__(self, code, ctype):
            self.status_code, self.headers = code, {'Content-Type': ctype}

    monkeypatch.setattr(download_slcs.requests, 'head', lambda *a, **k: R(200, 'text/html; charset=UTF-8'))
    assert download_slcs._probe('http://x/a.slc') == 'missing'
    monkeypatch.setattr(download_slcs.requests, 'head', lambda *a, **k: R(200, 'application/octet-stream'))
    assert download_slcs._probe('http://x/a.slc') == 'file'
    monkeypatch.setattr(download_slcs.requests, 'head', lambda *a, **k: R(404, 'text/html'))
    assert download_slcs._probe('http://x/a.slc') == 'missing'


def test_download_uavsar_slcs_creates_dir_and_skips_existing(tmp_path, monkeypatch):
    calls = []

    def fake(url, output_f):
        calls.append(url)
        _fake_stream_download(url, output_f)

    monkeypatch.setattr(download_slcs, 'stream_download', fake)
    out_dir = tmp_path / 'new' / 'slcs'
    urls = [f'{BASE}/Release30/lowman_05208_01/lowman_05208_01_BC_s1_2x8.llh',
            f'{BASE}/Release30/lowman_05208_01/lowman_05208_01_BC_s1_2x8.lkv']
    download_slcs.download_uavsar_slcs(urls, str(out_dir))
    download_slcs.download_uavsar_slcs(urls, str(out_dir))
    assert sorted(os.listdir(out_dir)) == ['lowman_05208_01_BC_s1_2x8.lkv', 'lowman_05208_01_BC_s1_2x8.llh']
    assert calls == urls
    with pytest.raises(TypeError):
        download_slcs.download_uavsar_slcs(['lowman_05208_01_[BC/BU]_s1_2x8.llh'], str(out_dir))
