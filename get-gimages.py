#!/usr/bin/env python

import argparse
import os, time, string, csv
import math
import requests

'''
As you read each row, if the timestamp is different- store the lat/lng, # satellites, bearing.
Calculate new bearing.

https://maps.googleapis.com/maps/api/streetview?size=640x640&fov=90&pitch=0&location=37.4570291,-122.1901025
2018-05-30T14:01:07.000Z,37.495793611,-122.309246092,188.229,12,POI
'''


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


def bearing(lat,lng, lat2,lng2):
  # lat/lng   = current gps. floats
  # lat2/lng2 = next gps. floats
  teta1 = math.radians(lat)
  teta2 = math.radians(lat2)
  delta1 = math.radians(lat2-lat)
  delta2 = math.radians(lng2-lng)

  y = math.sin(delta2) * math.cos(teta2)
  x = math.cos(teta1)*math.sin(teta2) - math.sin(teta1)*math.cos(teta2)*math.cos(delta2)
  brng = math.atan2(y,x)
  brng = math.degrees(brng)  # radians to degrees
  brng = (int(brng) + 360) % 360

  return brng


def proc(finame, imaged):

  queryLimit = 2480
  queries = 0
  total_pois = 0
  total_readings = 0
  last_lat = 0.
  last_lng = 0.
  mrl = "http://maps.googleapis.com/maps/api/streetview?size=640x640&fov=90&heading={}&location={},{}"

  with open(finame, 'r') as fi:
    ficsv = csv.reader(fi)
    ficsv.next()  # throw away the header

    first_row = ficsv.next()  # first line of data
    last_lat = first_row[1]
    last_lng = first_row[2]
    total_readings = total_readings + 1
    last_row = first_row

    for row in ficsv:
      total_readings = total_readings + 1
      last_row = row

      if row[5] == "POI":
        total_pois = total_pois + 1
        lat = row[1]
        lng = row[2]
        lat_f = float(lat)
        lng_f = float(lng)
        heading = str(bearing(float(last_lat),float(last_lng), lat_f,lng_f))
        print heading,
        print mrl.format(heading,lat,lng)
        r = requests.get(mrl.format(heading,lat,lng))
        if r.status_code != requests.codes.ok:
          print "Stopping due to error response from Google."
          break

        foname = os.path.join(imaged, row[0]+'_'+heading+'.jpg')
        with open(foname, 'wb') as fo:
          fo.write(r.content)

        queries = queries + 1
        if queries == queryLimit:
          print "Stopping due to Google query limit exceeded."
          break
        time.sleep(0.25)

    print("Total GPS Readings: {}. Total POIs: {}.".format(total_readings, total_pois))


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description='Get image for each POI Lat/long position.\n' + \
           'Program stops at 2500 updates or if server returns an error.')
  parser.add_argument('-c','--capture', help='Capture CSV filename', required=True)
  parser.add_argument('-i','--image', help='Directory to store images', required=True)
  args = vars(parser.parse_args())

  proc( args['capture'], args['image'] )

