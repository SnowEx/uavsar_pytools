import numpy as np
import rasterio as rio

def calc_inc_angle(dem, lkv_x, lkv_y, lkv_z, pixel_size=5.556):
    """
    Calculates UAVSAR incidence angle from DEM and look vector components.

    Parameters
    ----------
    dem, lkv_x, lkv_y, lkv_z : np.array or str
        Elevation data and the three components of the look vector.
        Strings are treated as filepaths to be handled by rasterio.
        Look vector should be pointing radar-to-ground. 
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
            dem_arr = src.read(1, out_dtype=np.float32)
            row_grad, col_grad = np.gradient(dem_arr, pixel_size)
            dem_shape = dem_arr.shape
    elif type(dem) == np.ndarray:
        row_grad, col_grad = np.gradient(dem.astype(np.float32), pixel_size)
        dem_shape = dem.shape
    else:
        raise ValueError('Pass filepath or np.array for DEM data.')

    # Map numpy row/col gradients to geographic x/y gradients
    dx = -col_grad
    dy = row_grad  

    # Calculate magnitude of surface normal vector (-dx, -dy, 1)
    norm_mag = np.sqrt(dx**2 + dy**2 + 1.0)

    # Read look vectors
    lkv = {}
    components = [lkv_x, lkv_y, lkv_z]
    directions = ['x','y','z']

    for comp_idx, vector in enumerate(components):
        if type(vector) == str:
            with rio.open(vector) as src:
                lkv[directions[comp_idx]] = src.read(1, out_dtype=np.float32)
        elif type(vector) == np.ndarray:
            assert vector.shape == dem_shape, 'Look vector data must be the same shape as DEM data.'
            lkv[directions[comp_idx]] = vector
        else:
            raise ValueError('Pass filepath or np.array for DEM data.')
        
    # Calculate look vector magnitude
    lkv_mag = np.sqrt(lkv['x']**2 + lkv['y']**2 + lkv['z']**2)
    lkv_mag[lkv_mag == 0] = np.nan

    # Negatives for dx and dy come from the definition of the surface normal vector 
    # Negatives for the lkv come from the radar-to-ground default direction
    dot_product = (-dx * -lkv['x']) + (-dy * -lkv['y']) + (1.0 * -lkv['z'])

    # Normalize the dot product with the magnitudes to get cos(inc_angle)
    # Clipping avoids floating point errors 
    inc_cos = np.clip(dot_product / (norm_mag * lkv_mag), -1.0, 1.0)
    return np.rad2deg(np.arccos(inc_cos))
    