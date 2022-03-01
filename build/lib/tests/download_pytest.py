"""Tests for `uavsar_pytools` downloading functionality."""
import sys
sys.path.append('../')

from uavsar_pytools.download.download import download_image
import pandas as pd
from os.path import join, basename, isfile
import shutil
import pytest

@pytest.fixture
def img_download():
    out_dir = './data/imgs/'
    in_csv = './data/urls'
    url = pd.read_csv(in_csv, header = None).sample(1).values[0][0]
    download_image(url, out_dir, ann = False)
    return join(out_dir, basename(url))

def test_one(img_download):
    out_dir = './data/imgs/'
    in_csv = './data/urls'
    url = pd.read_csv(in_csv, header = None).sample(1).values[0][0]
    assert isfile(img_download)

@pytest.fixture
def clear_dir():
    tmp_dir = './data/imgs'
    shutil.rmtree(tmp_dir)

def test_two(clear_dir):
    assert 1 == 1
