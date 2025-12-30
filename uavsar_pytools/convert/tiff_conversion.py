"""
Improved functions convert polsar, insar, and other associated UAVSAR files from binary format to geoTIFFS in WGS84.
"""

import os
from os.path import isdir, exists, basename, dirname, join, isfile
from glob import glob
from re import L
from matplotlib.pyplot import polar
from tqdm import tqdm
import numpy as np
import pandas as pd
import pytz
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
from pyproj import Geod, Proj
import logging

log = logging.getLogger(__name__)
logging.basicConfig()

def get_encapsulated(str_line, encapsulator):
    """
    Returns items found in the encapsulator, useful for finding units
    Originally written by Micah J. Amended for uavsar_pytools by Zach Keskinen.
    Args:
        str_line: String that has encapusulated info we want removed
        encapsulator: string of characters encapusulating info to be removed
    Returns:
        result: list of strings found inside anything between encapsulators
    e.g.
        line = 'density (kg/m^3), temperature (C)'
        ['kg/m^3', 'C'] = get_encapsulated(line, '()')
    """

    result = []

    if len(encapsulator) > 2:
        raise ValueError('encapsulator can only be 1 or 2 chars long!')

    elif len(encapsulator) == 2:
        lcap = encapsulator[0]
        rcap = encapsulator[1]

    else:
        lcap = rcap = encapsulator

    # Split on the lcap
    if lcap in str_line:
        for i, val in enumerate(str_line.split(lcap)):
            # The first one will always be before our encapsulated
            if i != 0:
                if lcap != rcap:
                    result.append(val[0:val.index(rcap)])
                else:
                    result.append(val)

    return result

def read_annotation(ann_file):
    """
    .ann files describe the INSAR data. Use this function to read all that
    information in and return it as a dictionary
    Originally written by Micah J. Amended for uavsar_pytools by Zach Keskinen.

    Expected format:
    `DEM Original Pixel spacing (arcsec) = 1`
    Where this is interpretted as:
    `key (units) = [value]`
    Then stored in the dictionary as:
    `data[key] = {'value':value, 'units':units}`
    values that are found to be numeric and have a decimal are converted to a
    float otherwise numeric data is cast as integers. Everything else is left
    as strings.
    Args:
        ann_file: path to UAVSAR annotation file
    Returns:
        data: Dictionary containing a dictionary for each entry with keys
              for value, units and comments
    """

    with open(ann_file) as fp:
        lines = fp.readlines()
        fp.close()
    data = {}

    # loop through the data and parse
    for line in lines:

        # Filter out all comments and remove any line returns
        info = line.strip().split(';')
        comment = info[-1].strip().lower()
        info = info[0]
        # ignore empty strings
        if info and "=" in info:
            d = info.split('=')
            name, value = d[0], d[1]
            # Clean up tabs, spaces and line returns
            key = name.split('(')[0].strip().lower()
            units = get_encapsulated(name, '()')
            if not units:
                units = None
            else:
                units = units[0]

            value = value.strip()

            # Cast the values that can be to numbers ###
            if value.strip('-').replace('.', '').isnumeric():
                if '.' in value:
                    value = float(value)
                else:
                    value = int(value)

            # Assign each entry as a dictionary with value and units
            data[key] = {'value': value, 'units': units, 'comment': comment}

    # Convert times to datetimes
    if 'start time of acquistion for pass 1' in data.keys():
        for pass_num in ['1', '2']:
            for timing in ['start', 'stop']:
                key = f'{timing} time of acquisition for pass {pass_num}'
                dt = pd.to_datetime(data[key]['value'])
                dt = dt.astimezone(pytz.timezone('US/Mountain'))
                data[key]['value'] = dt
    elif 'start time of acquisition' in data.keys():
        for timing in ['start', 'stop']:
                key = f'{timing} time of acquisition'
                dt = pd.to_datetime(data[key]['value'])
                dt = dt.astimezone(pytz.timezone('US/Mountain'))
                data[key]['value'] = dt

    return data

def grd_tiff_convert(in_fp, out_dir, ann_fp = None, overwrite = 'user', debug = False):
    """
    Converts a single binary image either polsar or insar to geotiff.
    See: https://uavsar.jpl.nasa.gov/science/documents/polsar-format.html for polsar
    and: https://uavsar.jpl.nasa.gov/science/documents/rpi-format.html for insar
    and: https://uavsar.jpl.nasa.gov/science/documents/stack-format.html for SLC stacks.
    Originally written by Micah J. Amended for uavsar_pytools by Zach Keskinen.

    Args:
        in_fp (string): path to input binary file
        out_dir (string): directory to save geotiff in
        ann_fp (string): path to UAVSAR annotation file
    """

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        log.setLevel(logging.WARNING)

    out_fp = join(out_dir, basename(in_fp)) + '.tiff'

    # Determine type of image
    if isfile(out_dir):
        raise Exception('Provide filepath not the directory.')

    if not exists(in_fp):
        raise Exception(f'Input file path: {in_fp} does not exist.')

    exts = basename(in_fp).split('.')[1:]
    if len(exts) == 2:
        ext = exts[1]
        type = exts[0]
    elif len(exts) == 1:
        type = ext = exts[0]
    else:
        raise ValueError('Unable to parse extensions')
    log.info(f'Extenstion: {ext}, type : {type}')
    
    # Find annotation file in same directory if no user given one
    if not ann_fp:
        if ext == 'grd' or ext == 'slc':
            ann_fp = in_fp.replace(f'.{type}', '').replace(f'.{ext}', '.ann')
        else:
            ann_fp = in_fp.replace(f'.{ext}', '.ann')
        if not exists(ann_fp):
            search_base = '_'.join(basename(in_fp).split('.')[0].split('_')[:4])
            search_full = os.path.join(os.path.dirname(in_fp), f'{search_base}*.ann')
            log.debug(f'Glob search: {search_full}')
            ann_search = glob(search_full)
            if len(ann_search) == 1:
                ann_fp = ann_search[0]
            else:
                raise Exception('No ann file found in directory. Please specify ann filepath.')
        else:
            log.info(f'No annotation file path specificed. Using f{ann_fp}.')

    # Check for compatible extensions
    if type == 'zip':
        raise Exception('Can not convert zipped directories. Unzip first.')
    if type == 'dat' or type == 'kmz' or type == 'kml' or type == 'png' or type == 'tif':
        raise Exception(f'Can not handle {type} products')
    if type == 'ann':
        raise Exception(f'Can not convert annotation files.')

    # Check for slant range files and ancillary files
    anc = None
    if type == 'slope' or type == 'inc':
        anc = True
        log.info(f'Identified as ancillary')
    # Check if file already exists and for overwriting
    ans = 'N'
    if exists(out_fp):
            if overwrite == True:
                ans = 'y'
            elif overwrite == False:
                ans = 'n'
            else:
                ans = input(f'\nWARNING! You are about overwrite {out_fp}!.  '
                            f'\nPress Y to continue and any other key to abort: ').lower()
            if ans == 'y':
                os.remove(out_fp)

    if ans == 'y' or exists(out_fp) == False:

        # Read in annotation file
        desc = read_annotation(ann_fp)
        #pd.DataFrame.from_dict(desc).to_csv('../data/test.csv')
        if 'start time of acquisition for pass 1' in desc.keys():
            mode = 'insar'
        else:
            mode = 'polsar'
        log.info(f'Working with {mode}')

        # Determine the correct file typing for searching our data dictionary
        if not anc:
            if mode == 'polsar':
                if type == 'hgt':
                    search = type
                else:
                    polarization = basename(in_fp).split('_')[5][-4:]
                    if polarization == 'HHHH' or polarization == 'HVHV' or polarization == 'VVVV':
                            search = f'{type}_pwr'
                    else:
                        search = f'{type}_phase'
                    type = polarization

            elif mode == 'insar':
                if ext == 'grd':
                    if type == 'int':
                        search = f'grd_phs'
                    else:
                        search = 'grd'
                else:
                    if type == 'int':
                        search = 'slt_phs'
                    else:
                        search = 'slt'
        else:
            if type == 'inc':
                search = 'hgt'
            search = type

        log.debug(f'Searching with: {search}')

        # Pull the appropriate values from our annotation dictionary
        nrow = desc[f'{search}.set_rows']['value']
        ncol = desc[f'{search}.set_cols']['value']
        log.debug(f'rows: {nrow} x cols: {ncol} pixels')

        if ext == 'grd' or anc:
            # Ground projected images
            # Delta latitude and longitude
            dlat = desc[f'{search}.row_mult']['value']
            dlon = desc[f'{search}.col_mult']['value']
            log.debug(f'latitude delta: {dlat}, longitude delta: {dlon} deg/pixel')
            # Upper left corner coordinates
            lat1 = desc[f'{search}.row_addr']['value']
            lon1 = desc[f'{search}.col_addr']['value']
            log.debug(f'Ref Latitude: {lat1}, Longitude: {lon1} degrees')

            # Lat1/lon1 are already the center so for geotiff were good to go.
            t = Affine.translation(float(lon1), float(lat1))* Affine.scale(float(dlon), float(dlat))

            # Build the transform and CRS
            crs = CRS.from_user_input("EPSG:4326")

        # Get data type specific data
        bytes = desc[f'{search}.val_size']['value']
        endian = desc['val_endi']['value']
        log.debug(f'Bytes = {bytes}, Endian = {endian}')

        # Set up datatypes
        com_des = desc[f'{search}.val_frmt']['value']
        com = False
        if 'COMPLEX' in com_des:
            com = True
        log.debug(f'Complex descriptor {com_des}')
        if com:
            dtype = np.complex64
        else:
            dtype = np.float32
        log.debug(f'Data type = {dtype}')
        # Read in binary data
        z = np.fromfile(in_fp, dtype = dtype)

        # Reshape it to match what the text file says the image is
        if type == 'slope':
            z[z==-10000]= np.nan
            slopes = {}
            slopes['east'] = z[::2].reshape(nrow, ncol)
            slopes['north'] = z[1::2].reshape(nrow, ncol)
        else:
            slopes = None
            z = z.reshape(nrow, ncol)


        # Change zeros and -10,000 to nans based on documentation.
        if com:
            z[z== 0 + 0*1j] = np.nan + np.nan * 1j
        else:
            z[z==0]= np.nan
            z[z==-10000]= np.nan

        if slopes:
            slope_fps = []
            for direction, array in slopes.items():
                slope_fp = out_fp.replace('.tiff',f'.{direction}.tiff')
                log.debug(f'Writing to {slope_fp}...')
                dataset = rasterio.open(
                slope_fp,
                'w+',
                driver='GTiff',
                height=array.shape[0],
                width=array.shape[1],
                count=1,
                dtype=dtype,
                crs=crs,
                transform=t,)
                # Write out the data
                dataset.write(array, 1)

                dataset.close()
                slope_fps.append(slope_fp)
            return desc, z, type, slope_fps
        else:
            log.debug(f'Writing to {out_fp}...')

            if ext == 'grd' or anc:
                dataset = rasterio.open(
                    out_fp,
                    'w+',
                    driver='GTiff',
                    height=z.shape[0],
                    width=z.shape[1],
                    count=1,
                    dtype=dtype,
                    crs=crs,
                    transform=t,)
                log.info('Finished converting image to WGS84 Geotiff.')
            else:
                dataset = rasterio.open(
                    out_fp,
                    'w+',
                    driver='GTiff',
                    height=z.shape[0],
                    width=z.shape[1],
                    count=1,
                    dtype=dtype,)
            # Write out the data
            dataset.write(z, 1)

            dataset.close()

        return desc, z, type, out_fp

def array_to_tiff(arr, out_fp, desc, type):
    # Pull the appropriate values from our annotation dictionary
    nrow = desc[f'{type}.set_rows']['value']
    ncol = desc[f'{type}.set_cols']['value']
    # Pixel spacing
    dlat = desc[f'{type}.row_mult']['value']
    dlon = desc[f'{type}.col_mult']['value']
    # Upper left corner coordinates
    lat1 = desc[f'{type}.row_addr']['value']
    lon1 = desc[f'{type}.col_addr']['value']
    # Lat1/lon1 are already the center so for geotiff were good to go.
    t = Affine.translation(float(lon1), float(lat1))* Affine.scale(float(dlon), float(dlat))
    # Build the transform and CRS
    crs = CRS.from_user_input("EPSG:4326")

    dataset = rasterio.open(
        out_fp,
        'w+',
        driver='GTiff',
        height=arr.shape[0],
        width=arr.shape[1],
        count=1,
        dtype=arr.dtype,
        crs=crs,
        transform=t,
    )
    # Write out the data
    dataset.write(arr, 1)

    dataset.close()
