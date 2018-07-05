#!/usr/bin/env python

# TODO HDF5 output option.
# TODO switch to pandas.

import argparse
import csv
import h5py
import math
import os
import sys
import time

from datetime import datetime
import numpy as np

MIN_SATS = 4
'''
Takes 1 or more raw gps datasets in a directory, cleans the data,
write back an HDF5 file.
Rows look like this:

    TimeStamp,Lat,Lng,Altitude,NumSat,POI
    n/a,n/a,n/a,n/a,0,
    n/a,n/a,n/a,n/a,0,
    2011-11-19T01:25:00.690Z,n/a,n/a,n/a,0,
    2018-06-23T01:25:01.690Z,n/a,n/a,n/a,0,
    2018-06-23T01:25:01.690Z,n/a,n/a,n/a,10,
    2018-06-23T01:25:02.690Z,n/a,n/a,n/a,10,
    2018-06-23T01:25:03.690Z,n/a,n/a,n/a,10,
    2018-06-23T01:25:04.700Z,37.54856569,-122.302331958,23.326,10,
    2018-06-23T01:25:04.700Z,37.54856569,-122.302331958,23.326,12,

The data cleaning are the following steps:
1- Drop any rows with 'n/a's.
2- Drop any rows at dataset beginning if NumSat < MIN_SATS, but not later.
3- Calculate speed at each row.
4- Calculate heading in each row; relative or absolute. Use command argument flag.
5- Calculate summary: time duration of trip, avg speed, peak speed.
As each row is read, if the timestamp is different- store the lat/lng,
# satellites, bearing. Calculate new bearing.

'''

# The surface distance traversed, on earth, while traveling 1 degree of
# longitude at a latitude of about 40 degrees is approx 53.06 miles or 85.39 km.
# We'll use this as a good enough approximation anywhere in North America.
deg2miles = 53.06
deg2km = 85.39

# Offset in seconds to GMT
dt = datetime(1970,1,1,0,0,0)
zuluoffset = time.mktime(dt.utctimetuple())


def simple_distance(lat1,lng1, lat2,lng2):
  '''
  Simple Distance between two points with coordinates lat1,lng1 & lat2,lng2
  OK to use over short distances. The GPS distances at 1 sec intervals are very short.
  The units of the return value is degrees.
  '''
  return math.sqrt((lat1-lat2)**2.+(lng1-lng2)**2.)


def gcdistance(lat1,lng1, lat2,lng2):
  '''
  Great Circle Distance between two points with
  coordinates {lat1,lng1} and {lat2,lng2}
  '''
  #d = math.acos(math.sin(lat1)*math.sin(lat2)+math.cos(lat1)*math.cos(lat2)*math.cos(lng1-lng2))
  # equivalent formula, less subject to rounding error for short distances
  d = 2 * math.asin(math.sqrt( (math.sin((lat1-lat2)/2))**2 + 
            math.cos(lat1) * math.cos(lat2) * (math.sin((lng1-lng2)/2))**2 ))
  return d


def bearing(lat1,lng1, lat2,lng2):
  # lat1/lng1 = current gps. float
  # lat2/lng2 = next gps. float
  teta1 = math.radians(lat1)
  teta2 = math.radians(lat2)
  delta1 = math.radians(lat2-lat1)
  delta2 = math.radians(lng2-lng1)

  y = math.sin(delta2) * math.cos(teta2)
  x = math.cos(teta1)*math.sin(teta2) - math.sin(teta1)*math.cos(teta2)*math.cos(delta2)
  brng = math.atan2(y,x)
  brng = math.degrees(brng)  # radians to degrees
  brng = (int(brng) + 360) % 360

  return brng


def procFile(finame, outdir, absolute, kmph, verbose):
  '''
  Process a single CSV file.
  '''

  total_pois, total_readings, total_distance, total_time = 0, 0, 0., 0.
  bear, bear_last = 0, 0
  ts, ts_last = 0, 0
  speed_cumul = 0.0
  speed_peak = 0.0

  foname = os.path.abspath(os.path.join(outdir,os.path.basename(finame)))
  finame = os.path.abspath(finame)
  with open(finame, 'r') as fi, open(foname, 'w') as fo:
    ficsv = csv.DictReader(fi)
    fonames=ficsv.fieldnames[:]
    fonames.extend(['Speed','Bearing'])
    focsv = csv.DictWriter(fo, fieldnames=fonames)
    focsv.writeheader()

    first_row = True
    beginning = True
    # Drop any rows with 'n/a's.
    # Drop any rows at beginning if NumSat < MIN_SATS, but not later.
    for row in ficsv:
      # print row.values()
      if any(['n/a' in v for v in row.values()]):
        continue
      sats = int(row['NumSat'])
      if beginning and sats < MIN_SATS:
        continue
      else:
        beginning = False

      lat2, lng2 = float( row['Lat'] ), float( row['Lng'] )

      d = row['TimeStamp'].rstrip('Z')
      d,t = d.split('T')
      d = d.split('-')
      t = t.split(':')
      t[2] = t[2].split('.')[0]
      d = map(int, d)
      t = map(int, t)
      dt = datetime(d[0],d[1],d[2],t[0],t[1],t[2])
      ts = int(time.mktime(dt.utctimetuple()) - zuluoffset)

      if first_row:
        first_row = False
        row_last = row
        ts_last = ts
        dist = 0 
        bear = 0
        lat1, lng1 = lat2, lng2
      else:
        # Calculate distance in degrees.
        dist_deg = simple_distance(lat1,lng1, lat2,lng2)
        # Calculate absolute heading.
        bear = bearing(lat1,lng1, lat2,lng2)

      if ts == ts_last:
        continue

      row['TimeStamp'] = str(ts)

      # Calculate distance.
      if kmph:
        dist =    deg2km * dist_deg
      else:
        dist = deg2miles * dist_deg

      if absolute:
        row['Bearing'] = bear
      else:
        row['Bearing'] = bear - bear_last # TODO handle wraparound

      # Calculate speed.
      numsecs = ts - ts_last  # Can't assume 1/row, can loose rows going through tunnel.

      speed =  dist * 3600.0 / numsecs  # 
      row['Speed'] =  speed
      speed_cumul += speed
      if speed > speed_peak:
        speed_peak = speed

      total_time = total_time + numsecs
      total_distance = total_distance + dist
      total_readings = total_readings + 1
      poi = row['POI'] is not None and len(row['POI']) > 0
      if poi:
        total_pois = total_pois + 1

      # if dist != 0.0 or poi:
      # Store the timestamp, lat/lng, # satellites, speed, bearing.
      focsv.writerow(row)

      row_last = row
      ts_last = ts
      bear_last = bear
      lat1, lng1 = lat2, lng2

    focsv.writerow(row)

    speed_avg = speed_cumul / total_readings

  if verbose:
    # Summary: Trip duration, total distance traversed, avg speed, peak speed.
    if kmph:
      summary = "Total distance covered: {:.2f} kilometers; in {:.2f} hours\n" + \
              "Average speed: {:5.2f} kmph\n" + \
              "Peak    speed: {:5.2f} kmph\n" + \
                "Total Valid Readings: {:}\n" + \
                "Total POIs: {:,}"
    else:
      summary = "Total distance covered: {:.2f} miles; in {:.2f} hours\n" + \
              "Average speed: {:5.2f} mph\n" + \
              "Peak    speed: {:5.2f} mph\n" + \
                "Total Valid Readings: {:}\n" + \
                "Total POIs: {:,}"
    print(summary.format(total_distance, total_time/3600.0, speed_avg, speed_peak, \
          total_readings, total_pois))

  return total_readings, total_pois


def proc(path, outdir, absolute, kmph, verbose):
  '''
  Process all the CSV files found in a directory 
  or just a single file if that is what is given.
  '''
  total_readings, total_pois = 0, 0

  if os.path.isfile(path):
    total_readings, total_pois = procFile(path, outdir, absolute, kmph, verbose)

  if os.path.isdir(path):
    for root, dirs, files in os.walk(path):
      for file in files:
        if file.endswith(".csv"):
          readings, pois = procFile(os.path.join(root, file), outdir, absolute, kmph, verbose)
          total_readings += readings
          total_pois     += pois

  return total_readings, total_pois


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Prepare raw GPS data files')
  parser.add_argument('-v','--verbose', help='Will give summary at end', action='store_true')
  parser.add_argument('-r','--relative', help='Calculate relative heading in degrees', action='store_false')
  parser.add_argument('-a','--absolute', help='Calculate absolute heading in degrees; default', action='store_true')
  parser.add_argument('-k','--kmph', help='Calculates speed in KM/Hour. Default is MPH', action='store_true')
  parser.add_argument('-i','--in', help='Input file or directory', required=True)
  parser.add_argument('-o','--outdir', help='Place cleaned-up file(s) in this directory',
                                       required=False, default=os.getcwd())
  args = vars(parser.parse_args())

  absolute = args['absolute']
  if absolute is args['relative']:
    print("Must pick either absolute or relative.")
    sys.exit(1)

  absolute = False if args['relative'] is True else True # absolute is default.

  outdir = args['outdir']
  if not os.path.isdir(outdir):
    print("Specified output directory does not exist.")
    sys.exit(1)
  inpath = args['in']
  if not os.path.exists(inpath):
    print("Specified input path does not exist.")
    sys.exit(1)

  total_readings,total_pois = proc(inpath, outdir, absolute, args['kmph'], args['verbose'])

  print("Total GPS Readings: {:,}. Total POIs: {}.".format(total_readings, total_pois))
