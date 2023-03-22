import numpy as np
import pandas as pd
import datetime
import folium
import googlemaps
import polyline
from datadotgov_apis import *

## Enter your API Key
fileObject = open("apikey.txt", "r")
api_key = fileObject.read()
directions = googlemaps.Client(key=api_key)

## Get Directions
def get_direction(start, end, mode = 'driving'):
    departure_time = datetime.datetime.now()
    direction  = directions.directions(start, end, mode=mode)
    result = {}
    result.update({'duration': direction[0]['legs'][0]['duration']})
    result.update({'distance': direction[0]['legs'][0]['distance']})
    result.update({'directions': direction[0]['legs'][0]['steps']})
    return result

## Display on Map
def display_map(directions, taxi = [], carpark = pd.DataFrame({'carpark_list': [], 'carpark_latlog': [], 'availability': []})):
    colours = {'WALKING': 'blue', 'DRIVING': 'green', 'TRANSIT': 'green', 'BICYCLING': 'purple'}
    display = folium.Map()
    lower = []
    upper = []
    
    for i in taxi:
        folium.Marker([i[1], i[0]], icon=folium.Icon(color="orange", prefix='fa', icon="taxi")).add_to(display)
        lower.append([i[1], i[0]])
        upper.append([i[1], i[0]])
        
    for i in range(len(carpark)):
        folium.Marker(carpark['carpark_latlog'][i], icon=folium.Icon(color="green", prefix='fa', icon="car"), tooltip = 'Available Lots: ' + str(carpark['availability'][i])).add_to(display)
        lower.append(list(carpark['carpark_latlog'][i]))
        upper.append(list(carpark['carpark_latlog'][i]))
        
    routes = []
    travel_mode = []
    for i in directions:
        travel_mode.append(i['travel_mode'])
        subroute = []
        points = i["polyline"]["points"]
        decoded_points = polyline.decode(points)
        for point in decoded_points:
            subroute.append(list(point))
        routes.append(subroute)
    
    for i in range(len(routes)):
        if i == 0:
            folium.Marker(routes[i][0]).add_to(display)
        elif i == len(routes)-1:
            folium.Marker(routes[i][-1], icon=folium.Icon(color="red", prefix='fa', icon="flag")).add_to(display)
        
        folium.PolyLine(routes[i], color = colours[travel_mode[i]], weight=5).add_to(display)
        
        lower.append(pd.DataFrame(routes[i]).min().values.tolist())
        upper.append(pd.DataFrame(routes[i]).max().values.tolist())
        
    sw = (pd.DataFrame(lower).min()).values.tolist()
    ne = (pd.DataFrame(upper).max()).values.tolist()
    display.fit_bounds([sw, ne])
    return display
