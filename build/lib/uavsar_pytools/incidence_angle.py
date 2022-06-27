import numpy as np
import rasterio as rio


def arccos_theta(v):
    if v < 1 and v > -1:
        return np.arccos(v)
    elif v > 1 and v < 3:
        return np.arccos(2-v)
    elif v < -1 and v > -3:
        return np.arccos(-1 + 0.000001) - np.arccos(2+v)
    else:
        return np.nan

arccos_theta = np.vectorize(arccos_theta)


def calc_inc_angle(dem, lkv_x, lkv_y, lkv_z, pixel_size=5.556):
    """
    Calculates UAVSAR incidence angle from DEM and look vector components.

    Parameters
    ----------
    dem, lkv_x, lkv_y, lkv_z : np.array or str
        Elevation data and the three components of the look vector.
        Strings are treated as filepaths to be handled by rasterio.
    pixel_size : float
        Pixel size of all components in [m]. Default value is for 
        UAVSAR images from JPL.
    
    Returns
    -------
    inc : np.array
        Incidence angle in degrees.
    """
    # Calculate gradient of DEM
    if type(dem) == str:
        with rio.open(dem) as src:
            dem_arr = src.read(1)
            dx, dy = np.gradient(dem_arr, pixel_size)
            dem_shape = dem_arr.shape
    elif type(dem) == np.ndarray:
        dx, dy = np.gradient(dem, pixel_size)
        dem_shape = dem.shape
    else:
        raise ValueError('Pass filepath or np.array for DEM data.')

    # Look vectors
    lkv = {}
    components = [lkv_x, lkv_y, lkv_z]
    directions = ['x','y','z']

    for comp_idx, vector in enumerate(components):
        if type(vector) == str:
            with rio.open(vector) as src:
                lkv[directions[comp_idx]] = src.read(1)
        elif type(vector) == np.ndarray:
            assert vector.shape == dem_shape, 'Look vector data must be the same shape as DEM data.'
            lkv[directions[comp_idx]] = vector
        else:
            raise ValueError('Pass filepath or np.array for DEM data.')
        
    # Calculate look vector magnitude
    lkv_mag = np.zeros_like(lkv['x'])
    for direction, arr in lkv.items():
        lkv_mag = lkv_mag + arr**2
    lkv_mag = lkv_mag**0.5
    lkv_mag[lkv_mag == 0] = np.nan
    # Unit vectors
    unit_lkv = {}
    for direction, arr in lkv.items():
        unit_lkv[direction] = -arr/lkv_mag

    # Calculate incidence angle
    inc_cos = unit_lkv['x']*dx + unit_lkv['y']*dy + unit_lkv['z']
    inc = arccos_theta(inc_cos)

    return np.rad2deg(inc)
    