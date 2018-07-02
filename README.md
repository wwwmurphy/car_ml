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

