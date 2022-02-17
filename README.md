# uavsar_pytools

Python tools to download and convert binary Uavsar images from the Alaska Satellite Facility and Jet Propulsion Laboratory databases.

The fundemental class of uavsar_pytool is the UavsarScene that allows downloading, unzipping, and converting of binary Uavsar files into Geotiffs in WGS84. The two required inputs are a url to a

```python
from uavsar_pytools.UavsarScene import UavsarScene
zip_url = 'https://datapool.asf.alaska.edu/INTERFEROMETRY_GRD/UA/INTERFEROGRAM_OR_POLSAR_GRD.zip'
image_directory = '~/directory/to/store/images/'
scene = UavsarScene(url = zip_url, work_dir= image_directory)
scene.url_to_tiffs()
scene.show(i = 1)
```
