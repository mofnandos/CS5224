# -*- coding: utf-8 -*-
"""CS5224 Project DataDotGov APIs"""

# Commented this out cause it causes error
#try:
#  ! pip install pgeocode
#  ! pip install haversine
#  ! pip install geopy
#  ! pip install pyproj
#except:
#  print("Something not installed")

import pgeocode
import requests # HTTP requests (GET / POST)
import datetime
import pandas as pd
import numpy as np
import folium
import json
from pyproj import Transformer
from geopy.geocoders import Nominatim
from haversine import haversine, Unit
from IPython.display import display, Image



"""## Helper Functions"""

def address_to_coord(address):
  # calling the Nominatim tool
  loc = Nominatim(user_agent="GetLoc")
  getLoc = loc.geocode(address)
  place_lat = getLoc.latitude
  place_long = getLoc.longitude
  place_coord = (place_lat, place_long)
  return place_coord

def postalcode_to_coord(postal_code):
  nomi = pgeocode.Nominatim('sg')
  place = nomi.query_postal_code(postal_code)
  place_lat = place['latitude']
  place_long = place['longitude']
  place_coord = (place_lat, place_long)
  return place_coord



"""# Carpark Availability API
## Initialization: Getting the list of HDB Carpark
"""

def carpark_init(file_name):
  df_hdb_cp = pd.read_csv(file_name)

  transformer = Transformer.from_crs("EPSG:3414", "EPSG:4326")

  df_hdb_cp['lat'], df_hdb_cp['log'] = transformer.transform(df_hdb_cp['y_coord'], df_hdb_cp['x_coord'])
  df_hdb_cp['lat_log'] = list(zip(df_hdb_cp['lat'],df_hdb_cp['log']))
  
  return df_hdb_cp

"""## Finding the nearest carpark"""

def nearest_carpark(place_coord, walking_dist_to_cp, df_hdb_cp): ## added df_hdb_cp into the function
  nearest_carpark_num_list = []
  nearest_carpark_latlog_list = []
  for i in range(df_hdb_cp.shape[0]):
    if haversine(df_hdb_cp['lat_log'][i], place_coord, unit=Unit.METERS) < walking_dist_to_cp:
      nearest_carpark_num_list.append(df_hdb_cp['car_park_no'][i])
      nearest_carpark_latlog_list.append(df_hdb_cp['lat_log'][i])
  return nearest_carpark_latlog_list, nearest_carpark_num_list



"""## Finding the nearest HDB carpark with availability data"""

def hdb_carpark_availability(nearest_carpark_list):
  # Obtaining carpark availability
  today = datetime.datetime.today()
  params = {"date_time": today.strftime("%Y-%m-%dT%H:%M:%S")} # YYYY-MM-DD 
  car = requests.get('https://api.data.gov.sg/v1/transport/carpark-availability', params=params).json()

  df = pd.DataFrame.from_dict(car['items'][0]['carpark_data'])

  # set of carpark which we have availability details
  carpark_number_set = set()
  for i in range(df.shape[0]):
    carpark_number_set.add(df['carpark_number'][i])

  carpark = {}

  if len(nearest_carpark_list) > 0:
    for i in range(len(nearest_carpark_list)):
      carpark_number = nearest_carpark_list.pop()
      if carpark_number in carpark_number_set:
        lots_available = df[df['carpark_number'] == carpark_number].iloc[0,0][0]['lots_available']
        carpark[carpark_number] = lots_available
  else:
    carpark['availability'] = 'No HDB carparks nearby'
  
  return carpark



"""# Taxi Availability API"""

def taxi_availability(place_coord, dist):
  # Taxi availability data
  today = datetime.datetime.today() 
  params = {"date": today.strftime("%Y-%m-%d")} # YYYY-MM-DD 
  taxi = requests.get('https://api.data.gov.sg/v1/transport/taxi-availability', params=params).json()
  num_taxi_all_singapore = taxi['features'][0]['properties']['taxi_count']

  taxi_list = taxi['features'][0]['geometry']['coordinates']
  taxi_near = []

  for taxi in taxi_list:
    taxi_tup = (taxi[1], taxi[0])
    if haversine(taxi_tup, place_coord, unit=Unit.METERS) < dist:
      taxi_near.append(taxi)

  num_taxi_near_me = len(taxi_near)

  return num_taxi_all_singapore, num_taxi_near_me, taxi_near # (long,lat)


def plot_taxi_near_me(taxi_near):
# Plotting taxi near my location
  sg_map = folium.Map([1.3521, 103.8198], zoom_start = 12, tiles="Stamen Terrain")
  for coord in taxi_near:
      folium.Marker([coord[1], coord[0]]).add_to(sg_map)
  sg_map.save('taxi_availability.html')



"""# Weather Forecast"""

def get_weather_forecast():
  # 2-hour weather forecast data
  today = datetime.datetime.today() 
  params = {"date": today.strftime("%Y-%m-%d")} # YYYY-MM-DD 
  wx_forecast = requests.get('https://api.data.gov.sg/v1/environment/2-hour-weather-forecast', params=params).json()

  df = pd.DataFrame(wx_forecast['area_metadata']).merge(pd.DataFrame(wx_forecast['items'][-1]['forecasts']).reset_index(), how='inner', left_on='name', right_on='area')
  df = df[['area','forecast','label_location']]
  df['lat_log'] = None

  for i in range(df.shape[0]):
    df['lat_log'][i] = (df['label_location'][i]['latitude'], df['label_location'][i]['longitude'])

  df.drop(['label_location'], axis = 1, inplace = True)
  return df


def trip_weather_forecast(df_weather_forecast, start_place_coord, dest_place_coord):
  nearest_to_start = None
  nearest_to_dest = None

  dist_to_start = 1e10
  dist_to_dest = 1e10

  for i in range(df_weather_forecast.shape[0]):
    i_to_start = haversine(df_weather_forecast['lat_log'][i], start_place_coord, unit=Unit.METERS)
    if i_to_start < dist_to_start:
      dist_to_start = i_to_start
      nearest_to_start = i
    i_to_dest = haversine(df_weather_forecast['lat_log'][i], dest_place_coord, unit=Unit.METERS) 
    if i_to_dest < dist_to_dest:
      dist_to_dest = i_to_dest
      nearest_to_dest = i

  return (df_weather_forecast['area'][nearest_to_start], df_weather_forecast['forecast'][nearest_to_start]), \
         (df_weather_forecast['area'][nearest_to_dest], df_weather_forecast['forecast'][nearest_to_dest])
