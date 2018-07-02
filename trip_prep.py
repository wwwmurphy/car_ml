#!/usr/bin/env python

# TODO relative heading, trip summaries, KMpH option.
# TODO switch to pandas.

import argparse
import csv
import h5py
import math
import os
import requests
import string
import sys
import time

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


def procFile(finame, absolute, outdir, kmph, verbose):
  '''
  Process a single CSV file.
  '''

  total_pois, total_readings, total_distance, total_time = 0, 0, 0., 0.
  bear = 0.0

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

      if first_row:
        last_row = row
        first_row = False

      if row['TimeStamp'] == last_row['TimeStamp']:
        continue

      lat1, lng1 = float( last_row['Lat'] ), float( last_row['Lng'] )
      lat2, lng2 = float( row['Lat'] ), float( row['Lng'] )

      # Calculate distance.
      if kmph:
        dist =    deg2km * simple_distance(lat1,lng1, lat2,lng2)
      else:
        dist = deg2miles * simple_distance(lat1,lng1, lat2,lng2)
      # Calculate heading; relative or absolute.
      if absolute:
        bear = bearing(lat1,lng1, lat2,lng2)
      else:
        pass

      # Calculate speed.
      row['Speed'] =  dist * 3600.0  # 
      row['Bearing'] = bear

      total_readings = total_readings + 1
      poi = row['POI'] is not None and len(row['POI']) > 0
      if poi:
        total_pois = total_pois + 1

      if dist != 0.0 or poi:
        focsv.writerow(row)

      last_row = row
    # Store the timestamp, lat/lng, # satellites, distance, bearing.
    focsv.writerow(row)

  if verbose:
    # Summary: Trip duration, avg speed, peak speed.
    pass

  return total_readings, total_pois


def proc(path, absolute, outdir, kmph, verbose):
  '''
  Process all the CSV files found in a directory 
  or just a single file if that is what is given.
  '''
  if os.path.isfile(path):
    total_readings, total_pois = procFile(path, absolute, outdir, kmph, verbose)
    print("Total GPS Readings: {}. Total POIs: {}.".format(total_readings, total_pois))
    return

  if os.path.isdir(path):
    for root, dirs, files in os.walk(path):
      for file in files:
        if file.endswith(".csv"):
          total_readings, total_pois = procFile(os.path.join(root, file), absolute, outdir, kmph, verbose)
          print("Total GPS Readings: {}. Total POIs: {}.".format(total_readings, total_pois))
    return
  return


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Prepare raw GPS data files')
  parser.add_argument('-v','--verbose', help='Will give summary at end', action='store_true')
  parser.add_argument('-r','--relative', help='Calculate relative heading in degrees', action='store_false')
  parser.add_argument('-a','--absolute', help='Calculate absolute heading in degrees; default', action='store_true')
  parser.add_argument('-k','--kmph', help='Calculates speed in KM/Hour. Default is MPH', action='store_false')
  parser.add_argument('-i','--in', help='Input file or directory', required=True)
  parser.add_argument('-o','--outdir', help='Place cleaned-up file(s) in this directory',
                                       required=False, default=os.getcwd())
  args = vars(parser.parse_args())

  absolute = args['absolute']
  if not ( absolute is not args['relative'] ):
    print("Must pick either absolute or relative.")
    sys.exit(1)

  absolute = False if args['relative'] is True else True # absolute is default.

  proc( args['in'], absolute, args['outdir'], args['verbose'], args['kmph'] )

