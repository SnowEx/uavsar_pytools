from uavsar_pytools.download.download import download_image
from uavsar_pytools.convert.tiff_conversion import grd_tiff_convert
import os

class UavsarImg():
    """
    Class to handle individual uavsar images. Methods include downloading and converting images.



    """
    binary_fp = None
    ann_fp = None
    tiff_fp = None
    arr = None
    desc = None

    def __init__(self, url, overwrite = False, debug = False, download_dir = None):
        self.url = url
        self.download_dir = download_dir
        self.overwrite = False
        self.debug = debug

    def download(self, download_dir, ann = False):
        if not download_dir:
            download_dir = os.makedirs('./tmp/', exists_ok = True)
        self.binary_fp, self.ann_fp = download_image(self.url, output_dir= download_dir, ann = ann)

    def convert_to_tiff(self, binary_fp = None, tiff_fp = None, ann_fp = None, overwrite = False):
        if not tiff_fp:
            if not self.tiff_fp:
                os.path.dirname(self.binary_fp)
            else:
                tiff_fp = self.tiff_fp
        if not binary_fp:
            binary_fp = self.binary_fp
        if not ann_fp:
            ann_fp = self.ann_fp
        self.desc, self.arr = grd_tiff_convert(in_fp = binary_fp, out_fp = tiff_fp, ann_fp = ann_fp, overwrite = overwrite)
