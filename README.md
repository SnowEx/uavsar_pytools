# uavsar_pytools

<img src="https://github.com/SnowEx/uavsar_pytools/blob/main/title_figure.png" width="1600">

Python tools to download and convert binary Uavsar images from the Alaska Satellite Facility and Jet Propulsion Laboratory databases. Developed by Zachary Keskinen and Jack Tarricone with guidance from Dr. Hans Peter Marshall of Boise State University, Micah Johnson with m3works, and Micah Sandusky with m3works.

## Installing

This package is installable with pip. In the terminal enter the following command:

```console
pip install uavsar_pytools
```

You will need a .netrc file in your home directory. This is a special file that stores passwords and usernames to be accessed by programs. If you are already registered at either the alaska satellite facility or jet propulsion laboratory skip step 1. Otherwise: 

1. If you need a username and password register at [link](https://search.asf.alaska.edu/).

2. In a python terminal or notebook enter:
```python
from uavsar_pytools.uavsar_tools import create_netrc
create_netrc()
```

You will be asked to enter your username and password and a netrc file will be automatically generated for you.

## Usage

The fundamental class of uavsar_pytools is the `UavsarScene`. This class is used for downloading, unzipping, and converting binary UAVSAR files into Geotiffs in WGS84. In order to use the class you will need to instantiate an instance of the class to hold your specific url and the image data. Please see the included tutorial and code snippet below. After instantiating the class you can call `scene.url_to_tiffs()` to fully download and convert the Uavsar images into analysis ready tiffs. The two required inputs are a url to an ASF or JPL zip file (if looking to download a single image see `UavsarImage` in the included notebooks) and that has been ground referenced (must have a .grd or \_grd in the name) along with a directory that you want to store the image files in.

```python
from uavsar_pytools.UavsarScene import UavsarScene
zip_url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/INTERFEROGRAM_OR_POLSAR_GRD.zip'
image_directory = '~/directory/to/store/images/'
scene = UavsarScene(url = zip_url, work_dir= image_directory) #instantiating an instance of the UavsarScene class.
scene.url_to_tiffs()
```

To get each image's numpy array the class has an `scene.images` property that contains the type, description, and numpy array for each image in the zip file. This is available after running `scene.url_to_tiffs()`.

```python
print(scene.image[0]['type'] # figure out the type of the first image
scene.images[0]['array'] # get the first image numpy array for analysis
```

For quick checks to visualize the data there is also a convenience method `scene.show(i = 1)` that allows you to quickly visualize the first image, or by iterating on i = 2,3,4, etc all the images in the zip file. This method is only available after converting binary images to array with `scene.url_to_tiffs()`.

## Need more help?

The notebook folder in this repository has example notebooks for how to utilize this repository or reach out with questions, features, bugs, or anything else.
