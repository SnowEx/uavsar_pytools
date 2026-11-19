"""UavsarScene conversion and cleanup without network or real binaries."""
import os

import numpy as np
import pytest

from uavsar_pytools import uavsar_scene
from uavsar_pytools.uavsar_scene import UavsarScene

URL = 'https://example.org/alamos_35915_20005-003_20008-000_0007d_s01_L090_01_int_grd.zip'


def _setup(tmp_path, monkeypatch):
    scene = UavsarScene(URL, str(tmp_path), clean=True)
    scene.tmp_dir = str(tmp_path / 'tmp' / scene.pair_name)
    bin_dir = os.path.join(scene.tmp_dir, 'bin_imgs')
    os.makedirs(bin_dir)
    for name in ['a_L090HH_01.unw.grd', 'a_L090HH_01.ann']:
        open(os.path.join(bin_dir, name), 'w').close()
    sibling = tmp_path / 'tmp' / 'keep_me.txt'
    sibling.write_text('other scene data')
    calls = []

    def fake_convert(f, out_dir, ann_fp=None, overwrite=True, debug=False):
        calls.append((f, ann_fp))
        return {}, np.zeros(2), 'unw', os.path.join(out_dir, 'out.tiff')

    monkeypatch.setattr(uavsar_scene, 'grd_tiff_convert', fake_convert)
    return scene, bin_dir, sibling, calls


def test_binary_dir_uses_full_paths_and_cleans_only_own_dir(tmp_path, monkeypatch):
    scene, bin_dir, sibling, calls = _setup(tmp_path, monkeypatch)
    scene.binary_to_tiffs(binary_dir=bin_dir)
    assert calls[0][0] == os.path.join(bin_dir, 'a_L090HH_01.unw.grd')
    assert calls[0][1] == os.path.join(bin_dir, 'a_L090HH_01.ann')
    assert not os.path.exists(scene.tmp_dir)
    assert sibling.exists()


def test_explicit_ann_fp(tmp_path, monkeypatch):
    scene, bin_dir, _, calls = _setup(tmp_path, monkeypatch)
    scene.binary_to_tiffs(binary_dir=bin_dir, ann_fp='given.ann')
    assert calls[0][1] == 'given.ann'


def test_no_inputs_raises(tmp_path, monkeypatch):
    scene, _, _, _ = _setup(tmp_path, monkeypatch)
    with pytest.raises(Exception):
        scene.binary_to_tiffs()


def test_show_complex_and_real(tmp_path, monkeypatch):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    shown = []
    monkeypatch.setattr(plt, 'show', lambda: shown.append(True))
    scene = UavsarScene(URL, str(tmp_path))
    scene.images = {'int': {'array': np.ones((4, 4), dtype=np.complex64) * (1 + 1j), 'type': 'int'},
                    'cor': {'array': np.linspace(0, 1, 16).reshape(4, 4), 'type': 'cor'}}
    scene.show('int')
    scene.show('cor')
    scene.show('missing')
    assert len(shown) == 2
    plt.close('all')
