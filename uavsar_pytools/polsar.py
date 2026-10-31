"""
Overview slideshow of Polsar:
https://dges.carleton.ca/courses/IntroSAR/Winter2019/SECTION%203%20-%20Carleton%20SAR%20Training%20-%20SAR%20Polarimetry%20%20-%20Final.pdf

Relevant
Nielsen 2022: DOI 10.1109/LGRS.2022.3169994
Cloude and Pottier 1997 [DOI: 10.1109/36.551935]
"""

import re
import numpy as np
import pandas as pd
import rasterio as rio
from glob import glob
import os
from os.path import join, basename
import logging
from tqdm import tqdm
from itertools import combinations
from itertools import combinations_with_replacement
import matplotlib.pyplot as plt
from pathlib import Path
from uavsar_pytools.convert.tiff_conversion import read_annotation, array_to_tiff

log = logging.getLogger(__name__)

def pol_from_fp(fp):
    """
    Pulls the polarization out of a UAVSAR file name.

    The number of underscore separated fields varies between products, so the
    polarization is matched against the band and polarization field itself
    (e.g. L090HHHH) rather than found by position.

    Arguments
    ---------
    fp : str
        File path or name of a UAVSAR file, e.g. evergl_15704_09044_000_090616_L090HHHH_CX_02_grd.grd

    Returns
    -------
    pol : str
        Four character polarization, e.g. HHHH.
    """
    match = re.search(r'[A-Z]\d{3}([HV]{4})', basename(fp))
    assert match, f'Unable to find a polarization in file name: {basename(fp)}'
    return match.group(1)

def get_polsar_stack(in_dir, bounds = False):
    """
    Reads UAVSAR GRD files or tiffs from input directory.

    Arguments
    ---------
    in_dir : str
        Input directory that contains UAVSAR GRD data. Must have all 
        crossproducts (HHHH, HVHV, VVVV, HHHV, HVHV, and HVVV) and the 
        associated .ann file.

    
    bounds (optional) : Subset to row_min, row_max, col_min, col_max in pixels.
    
    Returns
    -------
    stack : np.array
        Array of size [rows x columns x 6] containing UAVSAR data.
    """
    req_pols = set(['VVVV', 'HVHV', 'HVVV', 'HHHV', 'HHVV', 'HHHH'])
    # Check for tiffs:
    fps = glob(join(in_dir, '*.tiff'))
    pol = {}

    if len(fps) == 0:
        log.info('No tiffs found. Searching for grd files.')
        # Read ann file
        ann_fp = glob(join(in_dir, '*.ann'))[0]
        desc = read_annotation(ann_fp)
        nrows = desc['grd_pwr.set_rows']['value']
        ncols = desc['grd_pwr.set_cols']['value']
        fps = glob(join(in_dir, '*.grd'))
        # Read GRD files
        for f in fps:
            name = pol_from_fp(f)
            # Complex variables
            if name == 'HVVV' or name == 'HHHV' or name == 'HHVV':
                dtype = np.complex64
            # Real variables
            else:
                dtype = np.float32
            # Memory map so a subset can be cut without reading the whole multi GB file
            arr = np.memmap(f, dtype = dtype, mode = 'r').reshape(nrows, ncols)
            if bounds:
                row_min, row_max, col_min, col_max = bounds
                arr = arr[row_min:row_max, col_min:col_max]
            arr = np.array(arr)
            arr[arr == 0] = np.nan
            pol[name] = arr
    else:
        
        csvs = glob(join(in_dir, '*.csv'))
        assert len(csvs) == 1, f'Expected one annotation csv next to the tiffs in {in_dir}, found {len(csvs)}'
        desc = pd.read_csv(csvs[0], index_col = [0]).to_dict()
        for f in fps:
            with rio.open(f) as src:
                arr = src.read(1)
            name = pol_from_fp(f)
            # Complex variables
            pol[name] = arr

    missing_pols = req_pols - req_pols.intersection(pol.keys())
    assert len(missing_pols) == 0, f'Missing required polarizations : {missing_pols}'
    stack = np.dstack([pol['HHHH'], pol['HHHV'], pol['HVHV'], pol['HVVV'], pol['HHVV'], pol['VVVV']])
        
    return stack, desc

def get_polsar_stack_carsar(in_dir, image_width):
    """
    Reads CarSAR slc files from input directory.

    Arguments
    ---------
    in_dir : str
        Input directory that contains CarSAR slc data. Must have HH, HV, VV, and VH pols. 
    
    Returns
    -------
    stack : np.array
        Array of size [6 x rows x columns] containing CarSAR data.
    """
    in_dir = Path(in_dir)  # make sure it's a Path object
    pol_keywords = ['HH', 'HV', 'VV', 'VH']  # polarization channels to search for
    width = image_width

    # Search for all .slc files and group them by polarization keyword
    slcs = {}
    for f in in_dir.glob('*.slc'):
        for pol in pol_keywords:
            if pol in f.name:
                slcs[pol] = np.fromfile(f, '>c8').reshape(-1, width)
                break  # only take the first matching pol per file

    # Check if we found the required polarizations
    required_pols = ['HH', 'HV', 'VV','VH']  # Modify as needed
    for pol in required_pols:
        if pol not in slcs:
            raise ValueError(f"Missing required polarization: {pol}")
            
    s_matrix_elements = {
        'HHHH': slcs['HH'] * np.conjugate(slcs['HH']),
        'HHHV': slcs['HH'] * np.conjugate(slcs['HV']),
        'HHVV': slcs['HH'] * np.conjugate(slcs['VV']),
        'HVHV': slcs['HV'] * np.conjugate(slcs['HV']),
        'HVVV': slcs['HV'] * np.conjugate(slcs['VV']),
        'VVVV': slcs['VV'] * np.conjugate(slcs['VV']),
    }
    HHHH = s_matrix_elements['HHHH']
    HHHV = s_matrix_elements['HHHV']
    HVHV = s_matrix_elements['HVHV']
    HVVV = s_matrix_elements['HVVV']
    HHVV = s_matrix_elements['HHVV']
    VVVV = s_matrix_elements['VVVV']
    
    stack = np.stack([HHHH, HHHV, HVHV, HVVV, HHVV, VVVV])
    
    return stack


def calc_C3(HHHH, HHHV, HVHV, HVVV, HHVV, VVVV):
    """
    Calculates covariance matrix C3 from individual UAVSAR pixel locations. 
    Formula derived from Cloude and Pottier 1997 [DOI: 10.1109/36.551935]

    Arguments
    ---------
    HHHH, HHHV, HVHV, HVVV, HHVV, VVVV : float
        The six components of UAVSAR GRD data.

    Returns
    -------
    C3 : np.array [3x3]
        C3 matrix with complex dtype.
    """
    # Lower triangular components
    c11 = HHHH
    c12 = np.sqrt(2)*HHHV
    c13 = HHVV
    c22 = 2*HVHV
    c23 = np.sqrt(2)*HVVV
    c33 = VVVV
    # Upper components are conjugates of lower components
    c21 = np.conjugate(c12)
    c31 = np.conjugate(c13)
    c32 = np.conjugate(c23)
    # Assemble C3 matrix
    C3 = np.array([[c11,c12,c13],
                   [c21,c22,c23],
                   [c31,c32,c33]])
    return C3


def C3_to_T3(C3):
    """
    Converts covariance matrix C3 to coherency matrix T3. Translation of the
    PolSARPro C3_to_T3 function which can be found here (in C):
    https://github.com/EO-College/polsarpro/blob/master/Soft/src/lib/util_convert.c
    
    Arguments
    ---------
    C3 : np.array [3x3]
        C3 matrix (use output from calc_C3 function)
    
    Returns
    -------
    T3 : np.array [3x3]
        T3 matrix with complex dtype.
    """
    # Upper triangular components (PolSARpro T12, T13, T23)
    t11 = 0.5*(C3[0,0]+2*C3[0,2].real + C3[2,2])
    t12 = 0.5*(C3[0,0]-C3[2,2]) + (-C3[0,2].imag)*1j
    t13 = ((C3[0,1].real + C3[1,2].real) + (C3[0,1].imag - C3[1,2].imag)*1j)/np.sqrt(2)
    t22 = 0.5*(C3[0,0] - 2 * C3[0,2].real + C3[2,2])
    t23 = ((C3[0,1].real - C3[1,2].real) + (C3[0,1].imag + C3[1,2].imag)*1j)/np.sqrt(2)
    t33 = C3[1,1]
    # Lower components are conjugates of upper components
    t21 = np.conjugate(t12)
    t31 = np.conjugate(t13)
    t32 = np.conjugate(t23)
    # Assemble T3 matrix
    T3 = np.array([[t11,t12,t13],
                   [t21,t22,t23],
                   [t31,t32,t33]])
    
    return T3


def _nielsen_alphas(T3):
    """
    Alpha angles of the three eigenvectors of T3 using the eigenvector-eigenvalue
    identity of Nielsen 2022 [DOI: 10.1109/LGRS.2022.3169994].

    Where two eigenvalues are equal the identity is 0/0, so those pixels fall
    back to a direct eigendecomposition.

    Arguments
    ---------
    T3 : np.array [3x3] or [... x 3 x 3]

    Returns
    -------
    alphas : np.array [... x 3]
        Alpha angles in radians ordered by descending eigenvalue.
    values : np.array [... x 3]
        Eigenvalues in descending order.
    """
    T3 = np.asarray(T3)
    values = np.linalg.eigvalsh(T3)[..., ::-1]               # t1 >= t2 >= t3
    minors = np.linalg.eigvalsh(T3[..., 1:, 1:])[..., ::-1]  # m1 >= m2
    t1, t2, t3 = values[..., 0], values[..., 1], values[..., 2]
    m1, m2 = minors[..., 0], minors[..., 1]
    with np.errstate(divide='ignore', invalid='ignore'):
        e1 = np.sqrt(((t1 - m1)*(t1 - m2))/((t1 - t2)*(t1 - t3)))
        e2 = np.sqrt(((t2 - m1)*(t2 - m2))/((t2 - t1)*(t2 - t3)))
        e3 = np.sqrt(((t3 - m1)*(t3 - m2))/((t3 - t1)*(t3 - t2)))
    e = np.stack([e1, e2, e3], axis=-1)
    # Repeated eigenvalues: take |first component| of each eigenvector directly
    bad = ~np.all(np.isfinite(e), axis=-1)
    if np.any(bad):
        vectors = np.linalg.eigh(T3[bad])[1]
        e[bad] = np.abs(vectors[..., 0, ::-1])
    alphas = np.arccos(np.clip(e, 0, 1))
    return alphas, values


def T3_to_alpha1(T3):
    """
    Calculates alpha1 decomposition product from the coherency matrix T3. Uses
    the eigenvector-eigenvalue identity method described by Nielsen 2022 
    [DOI: 10.1109/LGRS.2022.3169994]. This is a per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    alpha_1 : float
        alpha 1 angle in degrees. 
    """
    alphas, _ = _nielsen_alphas(T3)
    return np.rad2deg(alphas[..., 0])

def vectorized_T3_to_alpha1(T3):
    """
    Vectorized alpha1 for a T3 stack of shape [3x3xheightxwidth]. Returns
    alpha 1 angle in degrees, shape [heightxwidth].
    """
    return T3_to_alpha1(np.transpose(T3, [2, 3, 0, 1]))

def T3_to_mean_alpha(T3):
    """
    Calculates mean alpha angle decomposition product from the coherency matrix 
    T3. Uses the eigenvector-eigenvalue identity method described by Nielsen 2022 
    [DOI: 10.1109/LGRS.2022.3169994]. This is a per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    mean_alpha : float
        mean alpha angle in degrees. 
    """
    alphas, values = _nielsen_alphas(T3)
    # Eigenvalue weighted mean of the three alpha angles
    weights = values / np.sum(values, axis=-1, keepdims=True)
    return np.rad2deg(np.sum(weights * alphas, axis=-1))

def vectorized_T3_to_mean_alpha(T3):
    """
    Vectorized mean alpha for a T3 stack of shape [3x3xheightxwidth]. Returns
    mean alpha angle in degrees, shape [heightxwidth].
    """
    return T3_to_mean_alpha(np.transpose(T3, [2, 3, 0, 1]))
    

def T3_to_H(T3):
    """
    Calculates entropy (H) decomposition product from the coherency matrix T3.
    Formula from Cloude and Pottier 1997 [DOI: 10.1109/36.551935]. This is a 
    per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    H : float
        Entropy (0 <= H <= 1).
    """
    values = np.linalg.eigvalsh(T3)
    total = np.sum(values)
    # A coherency matrix is positive semidefinite; anything else is not valid data
    if total <= 0 or np.any(values < -1e-9 * total):
        return np.nan
    weighted = np.clip(values, 0, None) / total
    nonzero = weighted > 0
    # 0 * log(0) is taken as 0
    h = -np.sum(weighted[nonzero] * np.log(weighted[nonzero]) / np.log(3))
    return h

def vectorized_T3_to_H(T3):
    """
    Calculates entropy (H) decomposition product from the coherency matrix T3.
    Formula from Cloude and Pottier 1997 [DOI: 10.1109/36.551935]. This is a 
    per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3xheightxwidth]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    H : np.array[heightxwidth]
        Entropy (0 <= H <= 1).
    """
    T3 = np.transpose(T3, (2, 3, 0, 1))

    # Compute eigenvalues
    values = np.linalg.eigvalsh(T3)  # Shape: [rows, cols, 3]

    # Normalize to get probabilities
    values_sum = np.sum(values, axis=-1, keepdims=True)
    weighted = values / values_sum

    # Mask to avoid log(0)
    with np.errstate(divide='ignore', invalid='ignore'):
        logweighted = np.log(weighted) / np.log(3)  # Base 3 log
        h = -np.nansum(weighted * logweighted, axis=-1)

    return h

def T3_to_A(T3):
    """
    Calculates anisotropy (A) decomposition product from the coherency matrix 
    T3. Formula from Cloude and Pottier 1997 [DOI: 10.1109/36.551935]. This is 
    a per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    A : float
        Anisotropy (0 <= H <= 1).
    """
    values = np.linalg.eigvalsh(T3)
    denom = values[1] + values[0]
    A = (values[1] - values[0]) / denom if denom > 0 else 0.0
    return A

def vectorized_T3_to_A(T3):
    """
    Calculates anisotropy (A) decomposition product from the coherency matrix 
    T3. Formula from Cloude and Pottier 1997 [DOI: 10.1109/36.551935]. This is 
    a per-pixel calculation.

    Arguments
    ---------
    T3 : np.array [3x3xheightxwidth]
        T3 matrix (use output from C3_to_T3 function)
    
    Returns
    -------
    A : np.array[heightxwidth]
        Anisotropy (0 <= H <= 1).
    """
    T3 = np.transpose(T3, (2, 3, 0, 1))
    values = np.linalg.eigvalsh(T3)
    denom = values[..., 1] + values[..., 0]
    A = np.divide(values[..., 1] - values[..., 0], denom, out=np.zeros_like(denom), where=denom > 0)
    return A


def decomp_components(stack, mean_alpha=True):
    """
    Function to calculate H-A-alpha (entropy-anisotropy-alpha) decomposition 
    from a stack of UAVSAR data. This function operates over the depth axis of 
    the stack and can be applied to an entire scene/array using 
    np.apply_along_axis. Can also calculate mean alpha using boolean keyword.

    Note if any cell location in the stack has one or more NaN elements it will
    that cell location will be skipped entirely. This enables functionality
    over entire UAVSAR scenes without having to mask NaN or clip rasters. 

    Arguments
    ---------
    stack : np.array
        Array of size [rows x cols x 6] containing UAVSAR data. Can use the output of 
        the get_polsar_stack function. 
    mean_alpha : bool (Default: True)
        If True, calculates and returns mean alpha product in addition to H, A, 
        and alpha.

    Returns
    -------
    H, A, alpha1 (opt. meanalpha) : float
        Decomposition products calculated at a given pixel location.
    """
    if np.any(np.isnan(stack)) or len(stack) != 6:
        if mean_alpha:
            return np.repeat(np.nan, 4)
        else:
            return np.repeat(np.nan, 3)
    # Matrices
    C3 = calc_C3(*stack)
    T3 = C3_to_T3(C3)
    # Decomposition products
    H = T3_to_H(T3)
    A = T3_to_A(T3)
    alpha1 = T3_to_alpha1(T3)
    
    if mean_alpha:
        meanalpha = T3_to_mean_alpha(T3)
        return H, A, alpha1, meanalpha
    else:
        return H, A, alpha1

def vectorized_decomp_components(stack, mean_alpha=True):
    """
    H-A-alpha (entropy-anisotropy-alpha) decomposition of a whole UAVSAR scene
    at once. Pixels with any NaN element are returned as NaN.

    Arguments
    ---------
    stack : np.array
        Array of size [rows x cols x 6] containing UAVSAR data in the order
        HHHH, HHHV, HVHV, HVVV, HHVV, VVVV. Can use the output of the
        get_polsar_stack function.
    mean_alpha : bool (Default: True)
        If True, calculates and returns mean alpha product in addition to H, A, 
        and alpha.

    Returns
    -------
    H, A, alpha1 (opt. meanalpha) : np.array [rows x cols]
        Decomposition products for the scene.
    """
    stack = np.moveaxis(np.asarray(stack), -1, 0)   # [6, rows, cols]
    assert stack.shape[0] == 6, 'Stack must have 6 polarimetric channels on the last axis.'
    valid = np.all(np.isfinite(stack), axis=0)
    # Fill invalid pixels with an identity covariance so the eigensolver runs
    # everywhere, then mask them out of the results.
    identity = np.array([1, 0, 0.5, 0, 0, 1], dtype=stack.dtype)[:, None, None]
    filled = np.where(valid, stack, identity)
    # calc_C3 and C3_to_T3 work elementwise, giving [3 x 3 x rows x cols]
    C3 = calc_C3(*filled)
    T3 = C3_to_T3(C3)
    H = vectorized_T3_to_H(T3)
    A = vectorized_T3_to_A(T3)
    alpha1 = vectorized_T3_to_alpha1(T3)
    products = [H, A, alpha1]
    if mean_alpha:
        products.append(vectorized_T3_to_mean_alpha(T3))
    return tuple(np.where(valid, p, np.nan) for p in products)
    

def uavsar_H_A_alpha(stack, parralel = False, mean_alpha=True):
    """
    Apply-along-axis version of decomp_products function. This function can be 
    used to perform H-A-alpha decomposition on a full UAVSAR scene. 

    Arguments
    ---------
    stack : np.array
        Array of size [rows x columns x 6] containing UAVSAR data. Can use the output of 
        the get_polsar_stack function. 
    mean_alpha : bool (Default: True)
        If True, calculates and returns mean alpha product in addition to H, A, 
        and alpha.

    Returns
    -------
    H, A, alpha1 (opt. meanalpha) : np.array
        Decomposition products calculated for the input scene. Size of all
        output arrays will match rows/cols of the input stack.
    """
    if parralel:
        import dask.array as da
        from dask.diagnostics import ProgressBar
        ProgressBar().register()
        res = da.apply_along_axis(decomp_components, axis = 2, arr = stack, mean_alpha=mean_alpha, dtype = stack.dtype).compute()
    else:
        res_shape = list(stack.shape[:2])
        res_shape.append(4 if mean_alpha else 3)
        res = np.empty(res_shape)
        iters = stack.shape[0]*stack.shape[1]
        for i, j in tqdm(np.ndindex(stack.shape[:2]), total = iters):
            res[i,j,:] = decomp_components(stack[i,j], mean_alpha=mean_alpha)
    H = res[:,:,0]
    A = res[:,:,1]
    alpha1 = res[:,:,2]
    if mean_alpha:
        mean_alpha = res[:,:,3]
        return H, A, alpha1, mean_alpha
    else:
        return H, A, alpha1

def vectorized_uavsar_H_A_alpha(stack, mean_alpha=True):
    """
    Vectorized H-A-alpha decomposition of a full UAVSAR scene.

    Arguments
    ---------
    stack : np.array
        Array of size [rows x columns x 6] containing UAVSAR data. Can use the output of 
        the get_polsar_stack function. 
    mean_alpha : bool (Default: True)
        If True, calculates and returns mean alpha product in addition to H, A, 
        and alpha.

    Returns
    -------
    H, A, alpha1 (opt. meanalpha) : np.array
        Decomposition products calculated for the input scene. Size of all
        output arrays will match rows/cols of the input stack.
    """
    return vectorized_decomp_components(stack, mean_alpha=mean_alpha)

def H_A_alpha_decomp(in_dir, out_dir, parralel = False):
    """
    in_dir must have all polarizations of []
    out_dir - must exist
    only works for UAVSAR
    """
    log.info('Collecting polsar stack')
    stack, desc = get_polsar_stack(in_dir)
    desc = read_annotation(glob(join(in_dir, '*.ann'))[0])
    log.info(f'Starting H, A, Alpha Calculations. Parralelized = {parralel}')
    H, A, alpha1, mean_alpha = uavsar_H_A_alpha(stack, parralel = parralel)
    d = {}
    d['entropy'] = H
    d['anisotropy'] = A
    d['alpha1'] = alpha1
    d['mean_alpha'] = mean_alpha
    os.makedirs(out_dir, exist_ok = True)
    for name, arr in d.items():
        out_fp = join(out_dir, name)
        array_to_tiff(arr, out_fp, desc = desc, type = 'grd_pwr')

def vectorized_H_A_alpha_decomp(in_dir, out_dir):
    """
    in_dir must have all polarizations of []
    out_dir - must exist
    only works for UAVSAR
    """
    log.info('Collecting polsar stack')
    stack, desc = get_polsar_stack(in_dir)
    log.info('Starting vectorized H, A, Alpha Calculations.')
    H, A, alpha1, mean_alpha = vectorized_uavsar_H_A_alpha(stack)
    d = {}
    d['entropy'] = H
    d['anisotropy'] = A
    d['alpha1'] = alpha1
    d['mean_alpha'] = mean_alpha
    os.makedirs(out_dir, exist_ok = True)
    for name, arr in d.items():
        out_fp = join(out_dir, name)
        array_to_tiff(arr, out_fp, desc = desc, type = 'grd_pwr')
