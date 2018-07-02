# car_ml
Utilities for auto trip capture using GPS logger, data prep, Spark processing, ML goodness.

## trip_prep.py

```
usage: trip_prep.py [-h] [-v] [-r] [-a] [-k] -i IN [-o OUTDIR]

Prepare raw GPS data files

optional arguments:
  -h, --help            show this help message and exit
  -v, --verbose         Will give summary at end
  -r, --relative        Calculate relative heading in degrees
  -a, --absolute        Calculate absolute heading in degrees; default
  -k, --kmph            Calculates speed in KM/Hour. Default is MPH
  -i IN, --in IN        Input file or directory
  -o OUTDIR, --outdir OUTDIR
                        Place cleaned-up file(s) in this directory
```


## get-gimages.py

```
usage: get-gimages.py [-h] -c CAPTURE -i IMAGE

Get image for each POI Lat/long position. Program stops at 2500 updates or if
server returns an error.

optional arguments:
  -h, --help            show this help message and exit
  -c CAPTURE, --capture CAPTURE
                        Capture CSV filename
  -i IMAGE, --image IMAGE
                        Directory to store images
```
