[![DOI](https://zenodo.org/badge/452858293.svg)](https://zenodo.org/badge/latestdoi/452858293)
![version](https://img.shields.io/badge/version-0.5.0-green)

# uavsar_pytools

<img src="https://github.com/SnowEx/uavsar_pytools/blob/main/title_figure.png" width="1600">

Python tools to download and convert binary Uavsar images from the Alaska Satellite Facility and Jet Propulsion Laboratory databases. Developed by Zachary Keskinen and Jack Tarricone with guidance from Dr. Hans Peter Marshall of Boise State University, Micah Johnson with m3works, and Micah Sandusky with m3works.

## Installing

This package is installable with pip. In the terminal enter the following command:

```console
pip install uavsar_pytools
```

## Authorization

You will need a [.netrc file](https://www.gnu.org/software/inetutils/manual/html_node/The-_002enetrc-file.html) in your home directory. This is a special file that stores passwords and usernames to be accessed by programs. If you are already registered at either the alaska satellite facility or jet propulsion laboratory skip step 1. Otherwise:

1. If you need a username and password register at [link](https://search.asf.alaska.edu/). Please ensure you have signed the end user agreement for Uavsar. You may need to attempt to download a uavsar image from vertex to prompt the end user agreement.

2. In a python terminal or notebook enter:
```python
from uavsar_pytools.uavsar_tools import create_netrc
create_netrc()
```

You will be asked to prompted to enter your username and password and a netrc file will be automatically generated for you. This file will be accessed during downloading and searching for Uavsar images. You will only need to generate this file once on your computer.

## Usage

The fundamental class of uavsar_pytools is the `UavsarScene`. This class is used for downloading, unzipping, and converting binary UAVSAR files into Geotiffs in WGS84. In order to use the class you will need to instantiate an instance of the class to hold your specific url and the image data. Please see the included tutorial and code snippet below. After instantiating the class you can call `scene.url_to_tiffs()` to fully download and convert the Uavsar images into analysis ready tiffs. The two required inputs are a url to an ASF or JPL zip file (if looking to download a single image see `UavsarImage` in the included notebooks) and that has been ground referenced (must have a .grd or \_grd in the name) along with a directory that you want to store the image files in.

```python
from uavsar_pytools import UavsarScene
## Example url. Use vertex to find other urls: https://search.asf.alaska.edu/
zip_url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/lowman_05208_21019-019_21021-007_0006d_s01_L090_01_int_grd.zip'

## Change this variable to a directory you want to download files into
image_directory = '~/directory/to/store/images/'

# Instantiating an instance of the UavsarScene class and downloading all images
scene = UavsarScene(url = zip_url, work_dir= image_directory)
scene.url_to_tiffs()
```

You will now have a folder of analysis ready tiff images in WGS84 from the provided url in your specificed work directory.

If you are interested in working with each image's numpy array the class has an `scene.images` property that contains the type, description, and numpy array for each image in the zip file. This is available after running `scene.url_to_tiffs()`.

```python
print(scene.image[0]['type'] # figure out the type of the first image
scene.images[0]['array'] # get the first image numpy array for analysis
```

For quick checks to visualize the data there is also a convenience method `scene.show(i = 1)` that allows you to quickly visualize the first image, or by iterating on i = 2,3,4, etc all the images in the zip file. This method is only available after converting binary images to array with `scene.url_to_tiffs()`.

### Downloading whole collections

Uavsar_pytools can now take a collection name and a start and end date and find, download, and process an entire collection of uavsar images. Collection names can be found at [campaign list](https://api.daac.asf.alaska.edu/services/utils/mission_list). Once you know your campaign name and the date range you can give the package a working directory along with the name and dates and it will do the rest. For example if you want to download all uavsar images for Grand Mesa, Colorado from November 2019 to April 2020 and wanted to save it to your documents folder you would use:

```python
from uavsar_pytools import UavsarCollection

## Collection name from the campaign list
col_name = 'Grand Mesa, CO'

## Working directory to save files into
work_d = '~/Documents/collection_ex/'

## Optional dates to check between
dates = ('2019-11-01','2020-04-01')

collection = UavsarCollection(collection = col_name, work_dir = work_d, dates = dates)

# Optional keywords: to keep binary files use `clean = False`, to download incidence angles 
# with each image use `inc = True`, for only certain pols use `pols = ['VV','HV']`.
# See docstring of class for full list.

collection.collection_to_tiffs()
```

Each image pair found will be placed in its own directory with its Alaska Satellite Facility derived name as the directory name. Unlike for UavsarScene this functionality will automatically delete the downloaded binary and zip files after converting them to tiffs to save space.

### Finding URLs for your images

The provided jupyter notebook tutorial in the notebooks folder will walk you through generating a bounding box for your area of interest and finding urls through the [asf_search api](https://github.com/asfadmin/Discovery-asf_search). However if you can also use the [vertex website](https://search.asf.alaska.edu/). After drawing a box and selecting UAVSAR from the platform selection pane (circled in red below) you will get a list of search results. Click on the ground projected image you want to download and right click on the download link (circled in orange below). Select ```copy link``` and you will have copied your relevant zip url.

<img src="https://github.com/SnowEx/uavsar_pytools/blob/main/vertex_example.png">

### Georeferencing SLC images to Ground Range

Note that this will require the extra packages (GDAL) specified in the setup.py. If you need this functionality please pip install using: `pip install uavsar_pytools[extra]`.

Single look complex (SLC) uavsar images and other Uavsar images without a .grd extension may be in [radar slant range](https://earth.esa.int/eogateway/missions/ers/radar-courses/radar-course-2#:~:text=The%20distance%20between%20any%20point,ground%20directly%20underneath%20the%20radar). This means that in order to view the image in the image in it's correct location you will need to project it to a coordinate system. The `geolocate_uavsar` function takes an array of lat, long, and heights called a .llh file and projects a uavsar image from radar to ground range. The .llh file is provided with slant range images in both the asf and jpl websites.

```
from uavsar_pytools.georeference import geolocate_uavsar
in_fp = '/change/to/path/to/slc/image.slc
ann_fp = '/path/to/annotation/file.ann
out_dir = '/directory/to/save/new/image
llh_fp = '/path/to/scenename.llh
out_fp = geolocate_uavsar(in_fp, ann_fp, out_dir, llh_fp):
```

The out_fp will be the file path to the newly created .tif file in your `out_dir`.

### Using new DEM to Generate Incidence Angle

The incidence angle file provided with the uavsar images is generated using the [SRTM dem](https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm-1). If you want to generate incidence angles using a high resolution dem use the `calc_inc_angle` function. This will require georeferencing the look vector file and exporting the x,y, and z components of this look vector.

```
from uavsar_pytools.incidence_angle import calc_inc_angle
dem = numpy array or .tif file path of dem resampled to match uavsar.
lkv_x = numpy array or .tif file path of x component of look vector file (.lkv)
lkv_y = numpy array or .tif file path of y component of look vector file (.lkv)
lkv_z = numpy array or .tif file path of z component of look vector file (.lkv)
calc_inc_angle(dem, lkv_x, lkv_y, lkv_z)
```

## Polarimetric Analysis

Polarimetric analysis of SAR images quantifies the scattering properties of objects in the scene using the phase differences between the various polarizations. A common analysis is to decompose these polarization differences into the mean alpha angle, entropy, and anisotropy. A great presentation on these terms and polarimetry is available from Carleton University [here](https://dges.carleton.ca/courses/IntroSAR/SECTION%204%20-%20Carleton%20SAR%20Training%20-%20SAR%20Polarimetry%20%20-%20Final.pdf). Uavsar_pytools provides functionality to decompose the [polsar uavsar images](https://uavsar.jpl.nasa.gov/science/documents/polsar-format.html#:~:text=UAVSAR%20data%20format%20for%20polarimetric,corresponding%20to%20the%20scattering%20matrix.) into the mean alpha, alpha 1 angle, entropy, and anisotropy.

```
from uavsar.polsar import H_A_alpha_decomp

# This should point to the directory with all 6 polarization
# (VVVV, HVHV, HVVV, HHHV, HHVV, HHHH) and the correct .ann file.
in_dir = '/path/to/directory/full/of/polsar.grd

# Will output 4 files to this directory of H, A, alpha1, and mean alpha.
out_dir = '/path/to/directory/to/output/H_A_Alpha_entropy
H_A_alpha_decomp(in_dir, out_dir)
```

Note that this function involves thousands of eigenvalue calculations and may be quite slow (~?? hours on a i7 @ 2.70 GHz for any image with ~74 million valid pixels). Considering putting the above into a python script instead of calling this from a jupyter notebook.
If you kernel dies due to memory overload use the `tiles = x` with x replaced with the number of tiles to tile the processing.

## Need more help?

The notebook folder in this repository has example notebooks for how to utilize this repository or reach out with questions, features, bugs, or anything else.
