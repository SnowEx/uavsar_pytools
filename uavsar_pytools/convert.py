"""
Originally written by Micah J. into python. Amended for uavsar_pytools by Zach Keskinen.
Functions convert polsar, insar, and other associated UAVSAR files from binary format to geoTIFFS in WGS84.
"""

import requests
import os
from os.path import isdir, exists, basename
from tqdm import tqdm
import pandas as pd
import pytz
import logging

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

def convert_image(in_fp, out_fp, ann_fp):
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
        raise Exception('Must provide file path to output file path.')
    extens = basename(in_fp).split('.')[1:]
        if len(extens) == 1:
            type = extens[0]
        elif len(extens) == 2:
            #sub_type = extens[0]
            type = extens[1]
        else:
            raise Exception('Can only handle one or two extensions on input file')

    ans = 'N'
    if exists(out_fp):
            ans = input(f'\nWARNING! You are about overwrite {in_fp}!.  '
                        f'\nPress Y to continue and any other key to abort: ').lower()
            if ans == 'y':
                os.remove(out_fp)

    if ans == 'y' or exists(out_fp) == False:

        desc = read_annotation(ann_fp)
        #pd.DataFrame.from_dict(desc).to_csv('../data/test.csv')








convert_image(in_fp = '../data/imgs/Rosamd_35012_21067_013_211124_L090VVVV_CX_01.grd', out_fp= '../data/imgs/test.tiff', ann_fp= '../data/imgs/Rosamd_35012_21067_013_211124_L090_CX_01.ann')