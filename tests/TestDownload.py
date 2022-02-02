"""Tests for `uavsar_pytools` downloading functionality."""
# remove path add once added to pypip
from genericpath import isfile
import sys
sys.path.append('../')

from uavsar_pytools.download import download_image
import pandas as pd
from os.path import join, basename, isfile

class TestDownload():
    # def test_one():
    #     urls = pd.read_csv('./data/urls')
    #     print(urls)
    #     for url in urls:
    #         download_image(url, out_dir)
    #         assert(isfile(join('./data/imgs', basename(url))))
    def test_one():
        out_dir = './data/urls'
        urls = pd.read_csv(out_dir)
        download_image(urls[0])
        assert isfile(join(out_dir, basename(url)))