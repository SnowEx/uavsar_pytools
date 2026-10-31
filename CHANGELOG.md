# Changelog

## 0.9.0 (unreleased)

Results change for every user of `calc_inc_angle` and for anyone with look vector
tifs from an earlier release. Read the first two items before upgrading.

### Incidence angle
- `calc_inc_angle` now normalizes the surface normal and pairs the DEM gradient
  with the look vector correctly (issues #53, #54). Previous results were wrong on
  every sloped pixel, with the facing and away response inverted.
- Look vector components are east, north, up, sensor to ground. `geolocate_uavsar`
  now writes them as `.lkv.x.tif` (east), `.lkv.y.tif` (north) and `.lkv.z.tif` (up).
  Files written by earlier releases have east and north swapped: regenerate them
  or swap the arguments.
- File inputs have nodata masked to NaN, take their pixel spacing from the
  geotransform and must be in a projected CRS. Array inputs accept a
  `(row, col)` pixel spacing.
- `arccos_theta` removed.

### Geocoding
- `geolocate_uavsar` drops the `.llh` zero fill, passes explicit output bounds
  (issue #34), parses the segment and multilook factor from the file names instead
  of assuming segment 1 at 2x8, refuses mismatched segments, checks array shapes
  before writing, and works in a private temp directory inside `out_dir`.
- `combo_llhs` writes little endian like every reader, orders segments
  numerically, writes `full.llh` next to the inputs and returns its path.

### Conversion
- `.hgt` and `.slope` keep zero as a valid value. Only -10000 is fill.
- `.inc` files use the `hgt` grid description from the annotation file.
- Binary byte order is read from the annotation file.
- `read_annotation` parses values in scientific notation, such as the 5.556e-05
  degree pixel spacing, as numbers instead of strings.
- Acquisition times for InSAR pairs are parsed to datetimes again (key typo).
- `unzip` matches polarizations as whole tokens and always extracts `.ann` files.

### Polarimetry
- `C3_to_T3` returned the conjugate of the coherency matrix. Off diagonal phases
  now have the right sign. Entropy, anisotropy and alpha were not affected.
- Vectorized H/A/alpha works and runs on the whole scene at once.
- Repeated eigenvalues no longer give NaN alpha angles or entropy.

### Snow depth inversion
- Array permittivity or density inputs no longer raise.
- Matzler permittivity coefficients are 1.5995 and 1.861 instead of 1.6 and 1.8.

### ASF catalogue change
- ASF replaced the per product UAVSAR collections with `UAVSAR_RPI` and
  `UAVSAR_POLSAR`, served as one url per file instead of a zip. `UavsarCollection`
  now searches by site code or geometry and processing level, downloads the ground
  projected files for the requested polarizations and converts them. The campaign
  filter no longer exists at ASF. Requires `asf_search >= 14.1`.
- `UavsarScene.files_to_tiffs(urls)` handles a scene given as a file list.
- A bare end date in `UavsarCollection(dates=...)` now covers that whole day. It used
  to end at midnight at the start of the day, so single day windows found nothing.
- `get_polsar_stack` memory maps the GRD files so a `bounds` window can be read
  without loading whole scenes.
- `environment.yml` now lists every runtime dependency including GDAL.

### Download and classes
- `download_image` returns a tuple when `ann=False`.
- `get_uavsar_slcs` found nothing under asf_search 14: it filtered on campaign and
  beam mode, which the new ASF collections do not carry. It now searches by site
  code and processing level, takes the flight line from the scene name, resolves
  the JPL release folder and BC/BU tag itself, and returns download ready urls
  keyed by flight line (issue #52). A version JPL does not have raises `ValueError`
  and an unreachable JPL host raises `ConnectionError` instead of probing for
  forty minutes. `download_uavsar_slcs` takes those urls, creates the output
  directory and skips files already present. Not run against JPL for this
  release: the download host was offline.
- `UavsarScene` removes only its own temp directory on clean, not `<work_dir>/tmp`.
- `UavsarImage` removes only its own binary and annotation files on clean.
- `UavsarImage.show` works for real and complex arrays.
- `create_netrc` writes the file from Python with mode 0600.

### Packaging
- `setup.py` no longer imports `argon2`; `pandas`, `pytz` and `pyproj` declared;
  unused `progressbar` and `folium` dropped.
- Importing the package no longer configures the root logger.
- Stale `build/` tree untracked.
- The wheel no longer installs the `tests` package into site-packages.
