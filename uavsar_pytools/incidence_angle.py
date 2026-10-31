import numpy as np
import rasterio as rio


def arccos_theta(v):
    """DEPRECATED: no longer used by calc_inc_angle.

    This helper folded out-of-range cosines (|v| > 1) back into arccos's domain.
    Such values only arose because calc_inc_angle previously dotted a unit look
    vector with an UNNORMALIZED surface normal (see GitHub issue #54). With the
    normal properly normalized the dot product is a true cosine, so only float
    round-off needs handling (np.clip). Kept temporarily for API compatibility.
    """
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
    Calculates UAVSAR local incidence angle from a DEM and look vector components:
    the angle between the ground->sensor line of sight and the local surface
    normal, LIA = arccos(l_hat . n_hat).

    Parameters
    ----------
    dem : np.array or str
        Elevation in meters on a NORTH-UP grid in a projected CRS (rows run
        south, columns run east, square pixels). Strings are treated as
        filepaths to be handled by rasterio.
    lkv_x, lkv_y, lkv_z : np.array or str
        Look vector components in EAST, NORTH, UP order, pointing from the
        SENSOR to the GROUND (the convention of JPL InSAR-Stack .lkv files).
        Any magnitude is accepted (e.g. slant range in meters); vectors are
        normalized internally.
    pixel_size : float
        Pixel size of all components in [m]. Default value is for
        UAVSAR images from JPL.

    Returns
    -------
    inc : np.array
        Local incidence angle in degrees.
    """
    # Calculate gradient of DEM
    if type(dem) == str:
        with rio.open(dem) as src:
            dem_arr = src.read(1)
    elif type(dem) == np.ndarray:
        dem_arr = dem
    else:
        raise ValueError('Pass filepath or np.array for DEM data.')
    # np.gradient returns (d/d_row, d/d_col); on a north-up grid rows run SOUTH
    # and columns run EAST, so dz/dEast = d_col and dz/dNorth = -d_row.
    d_row, d_col = np.gradient(dem_arr, pixel_size)
    zx = d_col                # dz/dEast
    zy = -d_row               # dz/dNorth
    dem_shape = dem_arr.shape

    # Look vectors (east, north, up), sensor->ground
    lkv = {}
    components = [lkv_x, lkv_y, lkv_z]
    directions = ['e', 'n', 'u']

    for comp_idx, vector in enumerate(components):
        if type(vector) == str:
            with rio.open(vector) as src:
                lkv[directions[comp_idx]] = src.read(1)
        elif type(vector) == np.ndarray:
            assert vector.shape == dem_shape, 'Look vector data must be the same shape as DEM data.'
            lkv[directions[comp_idx]] = vector
        else:
            raise ValueError('Pass filepath or np.array for look vector data.')

    # Unit ground->sensor look vector (negate sensor->ground, divide by magnitude)
    lkv_mag = np.sqrt(lkv['e']**2 + lkv['n']**2 + lkv['u']**2)
    lkv_mag[lkv_mag == 0] = np.nan
    le, ln, lu = -lkv['e']/lkv_mag, -lkv['n']/lkv_mag, -lkv['u']/lkv_mag

    # Unit surface normal n = (-zx, -zy, 1) / |(-zx, -zy, 1)|
    n_norm = np.sqrt(1.0 + zx**2 + zy**2)

    # cos(LIA) = l_hat . n_hat; a true cosine, so clip only float round-off
    inc_cos = (-zx*le - zy*ln + lu) / n_norm
    inc = np.arccos(np.clip(inc_cos, -1.0, 1.0))

    return np.rad2deg(inc)
