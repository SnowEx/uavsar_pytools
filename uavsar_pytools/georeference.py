from pathlib import Path
import os
import shutil
from glob import glob
from os.path import join, basename, dirname
import warnings
import numpy as np
import rasterio as rio
from osgeo import gdal, osr
from uavsar_pytools.convert.tiff_conversion import read_annotation, array_to_tiff
import rioxarray

def geocodeUsingGdalWarp(infile, latfile, lonfile, outfile,
                         insrs=4326, outsrs=None,
                         spacing=None, fmt='GTiff', bounds=None,
                         method='near'):
    '''
    From: Dr. Gareth Funning, UC Riverside, UNAVCO InSAR Short Course
    Geocode a swath file using corresponding lat, lon files
    '''
    sourcexmltmpl = '''    <SimpleSource>
      <SourceFilename>{0}</SourceFilename>
      <SourceBand>{1}</SourceBand>
    </SimpleSource>'''
    
    driver = gdal.GetDriverByName('VRT')
    tempvrtname = 'temp_ele.vrt'
    inds = gdal.OpenShared(infile, gdal.GA_ReadOnly)
    
    tempds = driver.Create(tempvrtname, inds.RasterXSize, inds.RasterYSize, 0)
    
    for ii in range(inds.RasterCount):
        band = inds.GetRasterBand(1)
        tempds.AddBand(band.DataType)
        tempds.GetRasterBand(ii+1).SetMetadata({'source_0': sourcexmltmpl.format(infile, ii+1)}, 'vrt_sources')
  
    sref = osr.SpatialReference()
    sref.ImportFromEPSG(insrs)
    srswkt = sref.ExportToWkt()
    tempds.SetMetadata({'SRS' : srswkt,
                        'X_DATASET': lonfile,
                        'X_BAND' : '1',
                        'Y_DATASET': latfile,
                        'Y_BAND' : '1',
                        'PIXEL_OFFSET' : '0',
                        'LINE_OFFSET' : '0',
                        'PIXEL_STEP' : '1',
                        'LINE_STEP' : '1'}, 
                        'GEOLOCATION')
    
    band = None
    tempds = None 
    inds = None
    
    if spacing is None:
        spacing = [None, None]
    warpOptions = gdal.WarpOptions(format=fmt,
                                xRes=spacing[0], yRes=spacing[0],
                                dstSRS=outsrs, outputBounds = bounds, dstNodata = -9999,
                                resampleAlg=method, geoloc=True)
    gdal.Warp(outfile, tempvrtname, options=warpOptions)
    os.remove('temp_ele.vrt')

def geolocate_uavsar(in_fp, ann_fp, out_dir, llh_fp):
    """
    Geolocates a uavsar image using an array of latitudes and longitudes.
    Can be either an SLC or Look Vector. If SLC will save as a tif of real
    and a tif of complex values.
    in_fp: file path of file to geolocate
    ann_fp: file path to annotation file
    out_dir: directory to save geolocated files
    llh_fp: file path to UAVSAR lat, long, elev files for georeferencing

    returns:
    List: files that have been created
    """

    desc = read_annotation(ann_fp)
    ext = basename(in_fp).split('.')[-1]

    tmp_dir = join(out_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
        
    nrows = desc[f'llh_1_2x8.set_rows']['value']
    ncols = desc[f'llh_1_2x8.set_cols']['value']
    dt = np.dtype('<f')

    arr = np.fromfile(llh_fp, dtype = dt)
    res = {}
    res[f'llh.lat'] = arr[::3].reshape(nrows, ncols)
    res[f'llh.long'] = arr[1::3].reshape(nrows, ncols)
    res[f'llh.dem'] = arr[2::3].reshape(nrows, ncols)

    profile = {
    'driver': 'GTiff',
    'interleave': 'band',
    'tiled': False,
    'nodata': 0,
    'width': ncols,
    'height':nrows,
    'count':1,
    'dtype':'float32'
    }
    
    # Save out tifs
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Dataset has no geotransform, gcps, or rpcs. The identity matrix be returned.")
        for name, arr in res.items():
            with rio.open(join(tmp_dir, name + '.tif'), 'w', **profile) as dst:
                dst.write(arr.astype(arr.dtype), 1)

    # Add VRT file for each tif
    tifs = glob(join(tmp_dir, '*.tif')) # list all .llh files
    for tiff in tifs: # loop to open and translate .llh to .vrt, and save .vrt using gdal
        raster_dataset = gdal.Open(tiff, gdal.GA_ReadOnly) # read in rasters
        raster = gdal.Translate(join(tmp_dir, basename(tiff).replace('.tif','.vrt')), raster_dataset, format = 'VRT', outputType = gdal.GDT_Float32)
    raster_dataset = None

    vrts = glob(join(tmp_dir, '*.vrt'))
    latf = [f for f in vrts if basename(f) == 'llh.lat.vrt'][0]
    longf = [f for f in vrts if basename(f) == 'llh.long.vrt'][0]

    profile = {
        'driver': 'GTiff',
        'interleave': 'band',
        'tiled': False,
        'nodata': 0,
        'width': ncols,
        'height':nrows,
        'count':1,
        'dtype':'float32'
        }

    if ext == 'slc':
        spacing = in_fp.replace(f'.{ext}','')[-3:]
        nrows = desc[f'{ext}_1_{spacing} rows']['value']
        ncols = desc[f'{ext}_1_{spacing} columns']['value']
        dtype = np.complex64
        arr = np.fromfile(in_fp, dtype = dtype).reshape(nrows, ncols)
        d_arrs = {}
        d_arrs['real'] = arr.real
        d_arrs['imag'] = arr.imag

    elif ext == 'lkv':
        spacing = in_fp.replace(f'.{ext}','')[-3:]
        nrows = desc[f'{ext}_1_{spacing} rows']['value']
        ncols = desc[f'{ext}_1_{spacing} columns']['value']
        dtype = np.dtype('<f')
        arr = np.fromfile(in_fp, dtype = dtype)
        d_arrs = {}
        d_arrs[f'y'] = arr[::3].reshape(nrows, ncols)
        d_arrs[f'x'] = arr[1::3].reshape(nrows, ncols)
        d_arrs[f'z'] = arr[2::3].reshape(nrows, ncols)

    elif ext == 'vrt':
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Dataset has no geotransform, gcps, or rpcs. The identity matrix be returned.")
            second_ext = basename(in_fp).split('.')[-2]
            if second_ext == 'unw':
                with rio.open(in_fp) as src:
                    # 1st band is amplitude, 2nd band is unwrapped phase
                    arr = src.read(2)
            else:
                with rio.open(in_fp) as src:
                    arr = src.read(1)
            d_arrs = {}
            ext = second_ext
            d_arrs[second_ext] = arr

    # Save out tifs
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Dataset has no geotransform, gcps, or rpcs. The identity matrix be returned.")
        for name, arr in d_arrs.items():
            with rio.open(join(tmp_dir, basename(in_fp) + f'.{name}.tif'), 'w', **profile) as dst:
                dst.write(arr.astype(arr.dtype), 1)

        tifs = glob(join(tmp_dir, f'*{ext}*.tif')) # list all .ext files
        for tiff in tifs: # loop to open and translate .ext to .vrt, and save .vrt using gdal
            raster_dataset = gdal.Open(tiff, gdal.GA_ReadOnly) # read in rasters
            raster = gdal.Translate(join(tmp_dir, basename(tiff).replace('.tif','.vrt')), raster_dataset, format = 'VRT', outputType = gdal.GDT_Float64)
        raster_dataset = None

        vrts = glob(join(tmp_dir, f'*{ext}*.vrt'))
        res_f = []
        for f in vrts:
            out_f = join(out_dir, basename(f).replace('vrt','tif'))
            geocodeUsingGdalWarp(infile = f,
                                latfile = latf,
                                lonfile = longf,
                                outfile = out_f,
                                spacing=[.00005556,.00005556])

            res_f.append(out_f)

        if ext == 'unw':
            print('Ignore the error message: Unable to compute bounds. It is related\n\
                to the pixels created by the conversion along the edge of topography.\n\
                Error message is known and should not be an issue.')
        
    shutil.rmtree(tmp_dir)

    return res_f

def reproject_clip_mask(in_fp, fp_to_match, out_fp):
    """
    Reproject, clip, and mask a tiff to another tiff.
    
    """
    xds = rioxarray.open_rasterio(in_fp)
    xds_match = rioxarray.open_rasterio(fp_to_match)
    xds_repr_match = xds.rio.reproject_match(xds_match)
    xds_repr_match.data[0][np.isnan(xds_match.data[0])] = np.nan
    xds_repr_match.rio.to_raster(out_fp)
    return out_fp

def combo_llhs(data_dir: Path):
    """
    Combines segment LLH files into a single combined llh file for georeferencing.
    """
    assert data_dir.exists()

    re_llhs = {'lat':[], 'lon': [], 'height':[]}
    for llh in sorted(data_dir.glob('*.llh')):
        segment = llh.stem.split('_')[-2].replace('s','')

        data = np.fromfile(llh, np.dtype('<f'))
        lat, lon, height = data[::3], data[1::3], data[2::3]
        for key, da in zip(re_llhs.keys(), [lat, lon, height]):
            re_llhs[key].extend(da)
    full = np.empty(len(re_llhs['lat'])*3, dtype='>f')
    full[0::3] = re_llhs['lat']
    full[1::3] = re_llhs['lon']
    full[2::3] = re_llhs['height']

    full.tofile('full.llh')

    return full
