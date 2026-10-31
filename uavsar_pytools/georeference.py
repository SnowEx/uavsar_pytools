from pathlib import Path
import os
import re
import shutil
import tempfile
import time
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
    fd, tempvrtname = tempfile.mkstemp(suffix='.vrt', prefix='geoloc_', dir=dirname(outfile) or '.')
    os.close(fd)
    inds = gdal.OpenShared(infile, gdal.GA_ReadOnly)
    
    tempds = driver.Create(tempvrtname, inds.RasterXSize, inds.RasterYSize, 0)
    
    for ii in range(inds.RasterCount):
        band = inds.GetRasterBand(ii+1)
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
                                xRes=spacing[0], yRes=spacing[1],
                                dstSRS=outsrs, outputBounds = bounds, dstNodata = -9999,
                                resampleAlg=method, geoloc=True)
    try:
        gdal.Warp(outfile, tempvrtname, options=warpOptions)
    finally:
        os.remove(tempvrtname)

def _segment_and_factor(fp):
    """
    Segment number and multilook factor from a stack file name,
    e.g. lowman_05208_01_BC_s2_2x8.llh -> ('2', '2x8').
    """
    match = re.search(r'_s(\d+)_(\d+x\d+)\.', basename(fp))
    if not match:
        raise ValueError(f'Cannot parse segment and multilook factor from {basename(fp)}')
    return match.group(1), match.group(2)


def _ann_dims(desc, prefix):
    """
    Rows and columns for an annotation key prefix such as 'slc_1_2x8'. Accepts
    both the 'prefix rows' and 'prefix.set_rows' key styles.
    """
    for rows_key, cols_key in [(f'{prefix} rows', f'{prefix} columns'),
                               (f'{prefix}.set_rows', f'{prefix}.set_cols')]:
        if rows_key in desc and cols_key in desc:
            return desc[rows_key]['value'], desc[cols_key]['value']
    raise KeyError(f'No rows/columns entry for {prefix} in annotation file')


def geolocate_uavsar(in_fp, ann_fp, out_dir, llh_fp):
    """
    Geolocates a uavsar image using an array of latitudes and longitudes.
    Can be either an SLC or Look Vector. If SLC will save as a tif of real
    and a tif of complex values.
    in_fp: file path of file to geolocate (.slc, .lkv or a .vrt on the same segment)
    ann_fp: file path to annotation file
    out_dir: directory to save geolocated files
    llh_fp: file path to UAVSAR lat, long, elev files for georeferencing.
        Must be the same segment as in_fp.

    returns:
    List: files that have been created
    """

    desc = read_annotation(ann_fp)
    ext = basename(in_fp).split('.')[-1]

    os.makedirs(out_dir, exist_ok=True)
    # Private temp dir so an existing out_dir/tmp or a stale run is never touched
    tmp_dir = tempfile.mkdtemp(prefix='geolocate_', dir=out_dir)

    try:
        # Lat/long grid dimensions for this segment and multilook factor
        llh_seg, llh_factor = _segment_and_factor(llh_fp)
        nrows, ncols = _ann_dims(desc, f'llh_{llh_seg}_{llh_factor}')
        dt = np.dtype('<f')

        arr = np.fromfile(llh_fp, dtype = dt)
        res = {}
        res['llh.lat'] = arr[::3].reshape(nrows, ncols)
        res['llh.long'] = arr[1::3].reshape(nrows, ncols)
        res['llh.dem'] = arr[2::3].reshape(nrows, ncols)

        # Latitudes and longitudes are 0 outside of the swath. Left in the geolocation
        # arrays gdal.Warp stretches the output grid from the scene all the way to
        # lat, long 0 and fails to invert the geolocation transform.
        valid = (res['llh.lat'] != 0) & (res['llh.long'] != 0)
        assert valid.any(), f'No valid latitudes and longitudes in {llh_fp}'
        for name in ['llh.lat', 'llh.long']:
            res[name] = np.where(valid, res[name], np.nan).astype('float32')
        bounds = (np.nanmin(res['llh.long']), np.nanmin(res['llh.lat']),
                  np.nanmax(res['llh.long']), np.nanmax(res['llh.lat']))

        profile = {
        'driver': 'GTiff',
        'interleave': 'band',
        'tiled': False,
        'nodata': np.nan,
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

        # Grid of the data file. SLC and LKV carry segment and multilook factor
        # in their names; a VRT is read for its size.
        if ext in ['slc', 'lkv']:
            seg, factor = _segment_and_factor(in_fp)
            if seg != llh_seg:
                raise ValueError(f'{basename(in_fp)} is segment {seg} but {basename(llh_fp)} is segment {llh_seg}')
            t_rows, t_cols = _ann_dims(desc, f'{ext}_{seg}_{factor}')
        elif ext == 'vrt':
            factor = llh_factor
            with rio.open(in_fp) as src:
                t_rows = src.height
                t_cols = src.width
        else:
            raise ValueError(f'Cannot geolocate a .{ext} file. Pass a .slc, .lkv or .vrt.')

        # Add VRT file for each tif, applying bilinear interpolation if grid sizes don't match
        tifs = glob(join(tmp_dir, '*.tif')) 
        for tiff in tifs: 
            raster_dataset = gdal.Open(tiff, gdal.GA_ReadOnly) 
            if t_rows != nrows or t_cols != ncols:
                raster = gdal.Translate(
                    join(tmp_dir, basename(tiff).replace('.tif','.vrt')), 
                    raster_dataset, 
                    format='VRT', 
                    outputType=gdal.GDT_Float32,
                    width=t_cols, 
                    height=t_rows, 
                    resampleAlg=gdal.GRA_Bilinear
                )
            else:
                raster = gdal.Translate(
                    join(tmp_dir, basename(tiff).replace('.tif','.vrt')), 
                    raster_dataset, 
                    format='VRT', 
                    outputType=gdal.GDT_Float32
                )
        raster_dataset = None

        vrts = glob(join(tmp_dir, '*.vrt'))
        latf = [f for f in vrts if basename(f) == 'llh.lat.vrt'][0]
        longf = [f for f in vrts if basename(f) == 'llh.long.vrt'][0]

        nrows, ncols = t_rows, t_cols
        # Zero is a valid data value, so nothing is flagged as nodata here
        profile = {
            'driver': 'GTiff',
            'interleave': 'band',
            'tiled': False,
            'nodata': np.nan,
            'width': ncols,
            'height':nrows,
            'count':1,
            'dtype':'float32'
            }

        if ext == 'slc':
            dtype = np.complex64
            arr = np.fromfile(in_fp, dtype = dtype).reshape(nrows, ncols)
            d_arrs = {}
            d_arrs['real'] = arr.real
            d_arrs['imag'] = arr.imag

        elif ext == 'lkv':
            dtype = np.dtype('<f')
            arr = np.fromfile(in_fp, dtype = dtype)
            # JPL .lkv is interleaved (east, north, up), sensor to ground.
            # Name them x = east, y = north, z = up to match calc_inc_angle.
            d_arrs = {}
            d_arrs['x'] = arr[::3].reshape(nrows, ncols)
            d_arrs['y'] = arr[1::3].reshape(nrows, ncols)
            d_arrs['z'] = arr[2::3].reshape(nrows, ncols)

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
                # rasterio silently resamples on a size mismatch, so check first
                assert arr.shape == (nrows, ncols), \
                    f'{name} array is {arr.shape} but the annotation grid is {(nrows, ncols)}'
                with rio.open(join(tmp_dir, basename(in_fp) + f'.{name}.tif'), 'w', **profile) as dst:
                    dst.write(arr.astype(arr.dtype), 1)

            tifs = glob(join(tmp_dir, f'*{ext}*.tif')) # list all .ext files
            for tiff in tifs: # loop to open and translate .ext to .vrt, and save .vrt using gdal
                raster_dataset = gdal.Open(tiff, gdal.GA_ReadOnly) # read in rasters
                raster = gdal.Translate(join(tmp_dir, basename(tiff).replace('.tif','.vrt')), raster_dataset, format = 'VRT', outputType = gdal.GDT_Float64)
            raster_dataset = None

            vrts = glob(join(tmp_dir, f'*{ext}*.vrt'))
            res_f = []

            # If 1x1 or 1x4, pass None to let GDAL auto-calculate the native high-res spacing
            warp_spacing = None if factor in ['1x1', '1x4'] else [.00005556, .00005556]

            for f in vrts:
                out_f = join(out_dir, basename(f).replace('vrt','tif'))
                geocodeUsingGdalWarp(infile = f,
                                    latfile = latf,
                                    lonfile = longf,
                                    outfile = out_f,
                                    spacing=warp_spacing, # Pass the dynamic spacing
                                    bounds = bounds)

                res_f.append(out_f)
    finally:
        # Short pause lets network file systems release handles before removal
        time.sleep(5)
        shutil.rmtree(tmp_dir, ignore_errors=True)

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
    Segments are appended in segment order. Returns the path of the combined file,
    written as full.llh in data_dir.
    """
    data_dir = Path(data_dir)
    assert data_dir.exists()

    llhs = sorted(data_dir.glob('*_s*_*.llh'), key=lambda fp: int(_segment_and_factor(fp)[0]))
    assert llhs, f'No segment .llh files found in {data_dir}'
    # Each file is row major interleaved (lat, lon, height), and segments stack
    # along rows, so appending the files keeps the layout.
    full = np.concatenate([np.fromfile(llh, np.dtype('<f')) for llh in llhs])

    out_fp = data_dir / 'full.llh'
    full.astype('<f').tofile(out_fp)

    return out_fp
