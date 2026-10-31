"""Offline tests of download helpers. Network calls are stubbed."""
import os


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


class _FakeResponse:
    headers = {'Content-Type': 'application/octet-stream'}

    def close(self):
        pass


def test_download_uavsar_slcs_creates_out_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(download_slcs.requests, 'get', lambda *a, **k: _FakeResponse())
    monkeypatch.setattr(download_slcs, 'stream_download', _fake_stream_download)
    out_dir = tmp_path / 'new' / 'slcs'
    files = ['lowman_05208_21006_003_210210_L090HH_01_[BC/BU]_s1_2x8.slc']
    download_slcs.download_uavsar_slcs(files, str(out_dir))
    assert (out_dir / 'lowman_05208_21006_003_210210_L090HH_01_BU_s1_2x8.slc').exists()


class _FakeGranule:
    properties = {'sceneName': 'UA_lowman_05208_21006_003_210210_L090_CX_01'}


def test_get_uavsar_slcs_empty_segments(monkeypatch):
    monkeypatch.setattr(download_slcs.asf, 'search', lambda **k: [_FakeGranule()])
    links = download_slcs.get_uavsar_slcs('lowman', getann=True, seg=[])
    assert links['lowman_05208'] == ['lowman_05208_21006_003_210210_L090HH_01_[BC/BU].ann']
