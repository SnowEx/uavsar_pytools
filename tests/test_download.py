def main():
    ## Testing ASF
    #url = 'https://unzip.asf.alaska.edu/INTERFEROMETRY_GRD/UA/grmesa_27416_21011-010_21016-002_0021d_s01_L090_01_int_grd.zip/grmesa_27416_21011-010_21016-002_0021d_s01_L090HH_01.cor.grd'
    #url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/lowman_05208_21019-019_21021-007_0006d_s01_L090_01_int_grd.zip'
    # url = 'https://datapool.asf.alaska.edu/INC/UA/Rosamd_35012_21067_013_211124_L090_CX_01.inc'
    # url = 'https://datapool.asf.alaska.edu/SLOPE/UA/Rosamd_35012_21067_013_211124_L090_CX_01.slope'
    # url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090_CX_01.ann'
    #url = 'https://unzip.asf.alaska.edu/STOKES/UA/Rosamd_35012_21067_013_211124_L090_CX_01_stokes.zip/Rosamd_35012_21067_013_211124_L090_CX_01.dat'
    #url = 'https://datapool.asf.alaska.edu/PAULI/UA/Rosamd_35012_21067_013_211124_L090_CX_01_pauli.tif'
    #url = 'https://unzip.asf.alaska.edu/COMPLEX/UA/Rosamd_35012_21067_013_211124_L090_CX_01_mlc.zip/Rosamd_35012_21067_013_211124_L090VVVV_CX_01.mlc'

    ## Testing JPL
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090HHHH_CX_01.mlc'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.dat'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090HHVV_CX_01.grd' ##didnt work
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.inc'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.slope'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.hgt'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.ann'
    # url =  'http://uavsar.asfdaac.alaska.edu/UA_peeler_13711_19084_020_191220_L090_CX_01/peeler_13711_19084_020_191220_L090_CX_01.mlc'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.cor'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.amp2.grd'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.ann'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090VVVV_CX_01.mlc'
    #url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090HHHV_CX_01.grd'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.inc'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.slope'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20008-000_20013-000_0007d_s01_L090_02/alamos_35915_20008-000_20013-000_0007d_s01_L090HH_02.amp1'
    # url = 'http://uavsar.asfdaac.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01.ann'
    url = 'https://uavsar.asf.alaska.edu/UA_alamos_35915_20013_000_200226_L090_CX_01/alamos_35915_20013_000_200226_L090_CX_01_grd.zip'
    download_InSAR(url, '../../data/', ann = True)

main()