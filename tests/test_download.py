"""Tests for `uavsar_pytools` downloading functionality."""
# remove path add once added to pypip
import sys
sys.path.append('../')

from uavsar_pytools.download import download
import pandas as pd


def main():
    urls = pd.read_csv('./data/urls')
    print(urls)
    for url in urls:
        pass
    #download_InSAR(url, '../../data/', ann = True)

main()