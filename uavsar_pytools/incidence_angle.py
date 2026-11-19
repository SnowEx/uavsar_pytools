from pathlib import Path
import numpy as np
import rasterio as rio


def _read_raster(fp):
    """Read band 1 of a GeoTIFF as float with nodata set to NaN.

    Returns the array, the (row, col) pixel spacing in CRS units and whether
    the CRS is geographic (degrees).
    """
    with rio.open(fp) as src:
        arr = src.read(1, masked=True).filled(np.nan).astype('float64')
        col_spacing, row_spacing = src.res
        geographic = src.crs is not None and src.crs.is_geographic
    return arr, (row_spacing, col_spacing), geographic


def calc_inc_angle(dem, lkv_x, lkv_y, lkv_z, pixel_size=5.556):
    """
    Calculates UAVSAR local incidence angle from a DEM and look vector components:
    the angle between the ground->sensor line of sight and the local surface
    normal, LIA = arccos(l_hat . n_hat).

    Parameters
    ----------
    dem : np.array, str or Path
        Elevation in meters on a NORTH-UP grid in a projected CRS (rows run
        south, columns run east). Paths are read with rasterio, nodata is
        masked to NaN and the pixel spacing is taken from the file, so
        ``pixel_size`` is ignored. Files in a geographic CRS (degrees) are
        rejected: reproject to UTM first.
    lkv_x, lkv_y, lkv_z : np.array, str or Path
        Look vector components in EAST, NORTH, UP order, pointing from the
        SENSOR to the GROUND (the convention of JPL InSAR-Stack .lkv files).
        Any magnitude is accepted (e.g. slant range in meters); vectors are
        normalized internally. Paths are read with nodata masked to NaN.
    pixel_size : float or (float, float)
        Pixel spacing in [m] used only when ``dem`` is an array. A single
        value means square pixels, a pair is (row spacing, column spacing).
        The default of 5.556 m is only correct for data resampled to that
        spacing, so pass the true spacing of your grid.

    Returns
    -------
    inc : np.array
        Local incidence angle in degrees. NaN wherever any input is NaN or
        nodata.
    """
    # DEM: from file (spacing from the geotransform) or from an array (spacing from pixel_size)
    if isinstance(dem, (str, Path)):
        dem_arr, spacing, geographic = _read_raster(dem)
        if geographic:
            raise ValueError('DEM is in a geographic CRS (degrees). Reproject to a projected CRS in meters first.')
    elif isinstance(dem, np.ndarray):
        dem_arr = dem.astype('float64')
        spacing = np.broadcast_to(np.asarray(pixel_size, dtype='float64'), (2,))
    else:
        raise ValueError('Pass filepath or np.array for DEM data.')
    dem_shape = dem_arr.shape

    # np.gradient returns (d/d_row, d/d_col); on a north-up grid rows run SOUTH
    # and columns run EAST, so dz/dEast = d_col and dz/dNorth = -d_row.
    d_row, d_col = np.gradient(dem_arr, spacing[0], spacing[1])
    zx = d_col                # dz/dEast
    zy = -d_row               # dz/dNorth

    # Look vectors (east, north, up), sensor->ground
    lkv = {}
    components = [lkv_x, lkv_y, lkv_z]
    directions = ['e', 'n', 'u']

    for comp_idx, vector in enumerate(components):
        if isinstance(vector, (str, Path)):
            arr, _, _ = _read_raster(vector)
        elif isinstance(vector, np.ndarray):
            arr = vector.astype('float64')
        else:
            raise ValueError('Pass filepath or np.array for look vector data.')
        assert arr.shape == dem_shape, 'Look vector data must be the same shape as DEM data.'
        lkv[directions[comp_idx]] = arr

    # Unit ground->sensor look vector (negate sensor->ground, divide by magnitude)
    lkv_mag = np.sqrt(lkv['e']**2 + lkv['n']**2 + lkv['u']**2)
    lkv_mag[lkv_mag == 0] = np.nan
    le, ln, lu = -lkv['e']/lkv_mag, -lkv['n']/lkv_mag, -lkv['u']/lkv_mag

    # Unit surface normal n = (-zx, -zy, 1) / |(-zx, -zy, 1)|
    n_norm = np.sqrt(1.0 + zx**2 + zy**2)

    # cos(LIA) = l_hat . n_hat; a true cosine, so clip only float round-off
    inc_cos = (-zx*le - zy*ln + lu) / n_norm
    inc = np.arccos(np.clip(inc_cos, -1.0, 1.0))
    # The central difference skips the pixel itself, so a nodata DEM pixel
    # would otherwise get a finite angle from its neighbours
    inc[np.isnan(dem_arr)] = np.nan

    return np.rad2deg(inc)
