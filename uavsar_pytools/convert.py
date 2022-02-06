"""
Originally written by Micah J. into python. Amended for uavsar_pytools by Zach Keskinen.
Functions convert polsar, insar, and other associated UAVSAR files from binary format to geoTIFFS in WGS84.
"""

import os
from os.path import isdir, exists, basename, dirname
from glob import glob
from tqdm import tqdm
import numpy as np
import pandas as pd
import pytz
import rasterio
from rasterio.transform import Affine
from rasterio.crs import CRS
import logging

from download import download_image

log = logging.getLogger(__name__)
logging.basicConfig()
log.setLevel(logging.DEBUG)

def get_encapsulated(str_line, encapsulator):
    """
    Returns items found in the encapsulator, useful for finding units
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

def convert_image(in_fp, out_fp, ann_fp = None):
    """
    Converts a single binary image either polsar or insar to geotiff.
    See: https://uavsar.jpl.nasa.gov/science/documents/polsar-format.html for polsar
    and: https://uavsar.jpl.nasa.gov/science/documents/rpi-format.html for insar.

    Args:
        in_fp (string): path to input binary file
        out_fp (string): path to save geotiff at
        ann_fp (string): path to UAVSAR annotation file
    """
    # Determine type of image
    if isdir(in_fp):
        raise Exception('Provide filepath not the directory.')

    if not exists(in_fp):
        raise Exception(f'Input file path: {in_fp} does not exist.')

    extens = basename(in_fp).split('.')[1:]
    if len(extens) == 1:
        type = extens[0]
        subtype = None
    elif len(extens) == 2:
        subtype = extens[0]
        type = extens[1]
    else:
        raise Exception('Can only handle one or two extensions on input file')

    if not ann_fp:
        if subtype:
            ann_fp = in_fp.replace(f'.{subtype}', '').replace(type, 'ann')
        else:
            ann_fp = in_fp.replace(type, 'ann')
        if not exists(ann_fp):
            search_base = ''.join(basename(in_fp).split('.')[0].split('_')[:4])
            ann_search = glob(os.path.join(os.path.dirname(in_fp), '{search_base}*.ann'))
            if len(ann_search) == 1:
                ann_fp = ann_search[0]
            else:
                raise Exception('No ann file found in directory. Please specify ann filepath.')
        else:
            log.info(f'No annotation file path specificed. Using f{ann_fp}.')

    # Check for compatible extensions
    if type == 'zip':
        raise Exception('Can not convert zipped directories. Unzip first.')
    if type == 'dat' or type == 'kmz' or type == 'kml' or type == '.png':
        raise Exception(f'Can not handle {type} products')
    if type == 'ann':
        raise Exception(f'Can not convert annotation files.')

    # Check for slant range files and ancillary files
    slant = None
    anc = None
    if type == 'slc' or type == 'mlc':
        slant = True
    if type == 'slope' or type == 'hgt' or type == 'inc':
        anc = True

    # Check if file already exists and for overwriting
    ans = 'N'
    if exists(out_fp):
            ans = input(f'\nWARNING! You are about overwrite {in_fp}!.  '
                        f'\nPress Y to continue and any other key to abort: ').lower()
            if ans == 'y':
                os.remove(out_fp)

    if ans == 'y' or exists(out_fp) == False:

        # Read in annotation file
        desc = read_annotation(ann_fp)
        #pd.DataFrame.from_dict(desc).to_csv('../data/test.csv')
        mode = desc['acquisition mode']['value']
        log.info(f'Working with {mode}')
        # Grab the metadata for building our georeference
        if not anc:
            if subtype != 'int' or subtype != None:
                type = f'{type}_pwr'
            else:
                type = f'{type}_mag'

        nrow = desc[f'{type}.set_rows']['value']
        ncol = desc[f'{type}.set_cols']['value']
        log.debug(f'rows: {nrow} x cols: {ncol} pixels')
        # Delta latitude and longitude
        dlat = desc[f'{type}.row_mult']['value']
        dlon = desc[f'{type}.col_mult']['value']
        if slant:
            log.debug(f'row delta: {dlat}, col delta: {dlon} m/pixel')
        else:
            log.debug(f'row delta: {dlat}, col delta: {dlon} deg/pixel')
        if slant:
            peg_lat = desc['Set_plat']['value'] # degrees
            peg_long = desc['Set_plon']['value'] # degrees
            peg_head = desc['Set_phdg']['value'] # degrees
            # Upper left corner coordinates
            lat1 = desc[f'{type}.row_addr']['value'] # meters of azimuth offset from peg of upper left pixel
            lon1 = desc[f'{type}.col_addr']['value'] # meters of range offset from peg of upper left pixel

            ################HOW TO SOLVE FOR LAT LONG? CAN WE USE GRD LAT LONGS OR DOES THE MULTILOOKING MAKE THAT WRONG?

            log.debug(f'Approximate radar latitude: {lat1}, longitude: {lon1} degrees')
        else:
            # Upper left corner coordinates
            lat1 = desc[f'{type}.row_addr']['value']
            lon1 = desc[f'{type}.col_addr']['value']
            log.debug(f'Ref Latitude: {lat1}, Longitude: {lon1} degrees')
        bytes = desc[f'{type}.val_size']['value']
        endian = desc['val_endi']['value']
        log.debug(f'Bytes = {bytes}, Endian = {endian}')

        # Set up datatypes
        com_des = desc[f'{type}.val_frmt']['value']
        com = False
        if 'COMPLEX' in com_des:
            com = True
        log.debug(f'Complex descriptor {com_des}')
        if subtype == 'int' or type == 'int':
            dtype = np.dtype([('real', '<f4'), ('imaginary', '<f4')])
        else:
            if com:
                dtype = np.dtype([('real', '<f4'), ('imaginary', '<f4')])
            else:
                dtype = np.dtype([('real', '<f{}'.format(bytes))])
        log.debug(f'Data type = {dtype}')
        # Read in binary data
        z = np.fromfile(in_fp, dtype = dtype)

        # Reshape it to match what the text file says the image is
        z = z.reshape(nrow, ncol)

        # Build the transform and CRS
        crs = CRS.from_user_input("EPSG:4326")

        log.debug(f'{lon1}, {lat1}, {dlon}, {dlat}')
        # Lat1/lon1 are already the center so for geotiff were good to go.
        t = Affine.translation(float(lon1), float(lat1))* Affine.scale(float(dlon), float(dlat))

        for i, comp in enumerate(['real', 'imaginary']):
            if comp in z.dtype.names:
                d = z[comp]
                log.debug('Writing to {}...'.format(out_fp))
                dataset = rasterio.open(
                    out_fp,
                    'w+',
                    driver='GTiff',
                    height=d.shape[0],
                    width=d.shape[1],
                    count=1,
                    dtype=d.dtype,
                    crs=crs,
                    transform=t,
                )
                # Write out the data
                dataset.write(d, 1)

                dataset.close()

if __name__ == '__main__':
    urls = pd.read_csv('../tests/data/urls')
    for url in tqdm(urls.iloc[:,0], unit = 'image'):
        if 'asf.alaska.edu' not in url:
            try:
                down_fp = download_image(url, output_dir = '../data/imgs', ann = True)
                convert_image(down_fp, out_fp = down_fp + '.tiff')
            except Exception as e:
                print(url)
                print(e)

# convert_image(in_fp = '../data/imgs/Rosamd_35012_21067_013_211124_L090VVVV_CX_01.grd', out_fp= '../data/imgs/test.tiff', ann_fp= '../data/imgs/Rosamd_35012_21067_013_211124_L090_CX_01.ann')