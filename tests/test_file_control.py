import os
from zipfile import ZipFile

from uavsar_pytools.convert.file_control import unzip


def test_unzip_polarization_filter(tmp_path):
    names = ['p_L090HH_01.unw.grd', 'p_L090HV_01.unw.grd', 'p_L090HHHV_CX_01.grd',
             'p_L090HH_01.ann', 'p_L090_CX_01.ann']
    zip_fp = tmp_path / 'scene.zip'
    with ZipFile(zip_fp, 'w') as z:
        for n in names:
            z.writestr(n, 'x')
    out = tmp_path / 'out'
    unzip(str(zip_fp), str(out), pols=['HH'])
    extracted = sorted(os.listdir(out))
    assert extracted == ['p_L090HH_01.ann', 'p_L090HH_01.unw.grd', 'p_L090_CX_01.ann']
