# uavsar_pytools

Python tools to download and convert binary Uavsar images from the Alaska Satellite Facility and Jet Propulsion Laboratory databases.

The fundamental class of uavsar_pytool is the '''UavsarScene'''. This class is used for downloading, unzipping, and converting binary Uavsar files into Geotiffs in WGS84. In order to use the class you will need to instantiate an instance of the class to hold your specific url and the image data. Please see the included tutorial and code snippet below. After instantiating the class you can call '''scene.url_to_tiffs()''' to fully download and convert the Uavsar images into analysis ready tiffs. The two required inputs are a url to an ASF or JPL zip file that has been ground referenced and a directory that you want to store the image files in.

```python
from uavsar_pytools.UavsarScene import UavsarScene
zip_url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/INTERFEROGRAM_OR_POLSAR_GRD.zip'
image_directory = '~/directory/to/store/images/'
scene = UavsarScene(url = zip_url, work_dir= image_directory)
scene.url_to_tiffs()
```

To get each image's numpy array the class has an '''scene.images''' property that contains the type, description, and numpy array for each image in the zip file. This is available after running '''scene.url_to_tiffs()'''.

'''python
print(scene.image[0]['type'] # figure out the type of the first image
scene.images[0]['array'] # get the first image numpy array for analysis
'''

For quick checks to visualize the data there is also a convenience method '''scene.show(i = 1)''' that allows you to quickly visualize the first image (or by iterating on i = 2,3,4, etc all the images in the zip file. This method is also available after converting binary images to array with '''scene.url_to_tiffs()'''

'''python

'''
