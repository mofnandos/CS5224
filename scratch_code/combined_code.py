from datadotgov_apis import *
from mapsdirection import *
import math
import time

df_hdb_cp = carpark_init('hdb-carpark-information.csv')
timing = -7201

if 'df_weather_forecast' not in locals():
    df_weather_forecast = get_weather_forecast()
    timing = time.time()
elif time.time() - timing >= (2 * 60 * 60):
    df_weather_forecast = get_weather_forecast()
    timing = time.time()

def get_options(start_address, end_address):
    
    ## Get lat and long of the address
    if math.isnan(postalcode_to_coord(start_address)[0]):
        start = address_to_coord(start_address)
    else:
        start = postalcode_to_coord(start_address)
    
    if math.isnan(postalcode_to_coord(end_address)[0]):
        end = address_to_coord(end_address)
    else:
        end = postalcode_to_coord(end_address)
        
    walk = get_direction(start, end, mode = 'walking')
    drive = get_direction(start, end, mode = 'driving')
    transit = get_direction(start, end, mode = 'transit')
    cycle = get_direction(start, end, mode = 'bicycling')
    
    walk_df = pd.DataFrame({'method': 'walk', 'duration': walk['duration']['text'], 'distance': walk['distance']['text']}, index = [0])
    drive_df = pd.DataFrame({'method': 'drive', 'duration': drive['duration']['text'], 'distance': drive['distance']['text']}, index = [1])
    transit_df = pd.DataFrame({'method': 'transit', 'duration': transit['duration']['text'], 'distance': transit['distance']['text']}, index = [2])
    cycle_df = pd.DataFrame({'method': 'cycle', 'duration': cycle['duration']['text'], 'distance': cycle['distance']['text']}, index = [3])
    
    mode_direction = {'walk': walk['directions'], 'drive': drive['directions'], 'transit': transit['directions'], 'cycle': cycle['directions']}
    
    carpark_latlog, carpark_list = nearest_carpark(end, 300, df_hdb_cp)
    carpark = pd.DataFrame({'carpark_list': carpark_list, 'carpark_latlog': carpark_latlog})
    
    availability = hdb_carpark_availability(carpark_list)
    availability_df = pd.DataFrame({'carpark_list': availability.keys(), 'availability': availability.values()})
    carpark = carpark.set_index('carpark_list').join(availability_df.set_index('carpark_list'), how = 'left')
    
    num_taxi_all_singapore, num_taxi_near_me, taxi_near = taxi_availability(start,500)
    start_weather_forecast, dest_weather_forecast = trip_weather_forecast(df_weather_forecast, start, end)
        
    return {'mode_comparison': pd.concat([walk_df, drive_df, transit_df, cycle_df]), 'mode_direction': mode_direction, 'carpark': carpark, 'num_taxi': num_taxi_near_me, 'taxi_latlong': taxi_near, 'start_weather_forecast': start_weather_forecast, 'dest_weather_forecast': dest_weather_forecast}

def plot_selection(start_address, end_address, mode_selected, information):
    if mode_selected == 'taxi':
        plot = display_map(information['mode_direction']['drive'], taxi = information['taxi_latlong'])
    elif mode_selected == 'drive':
        plot = display_map(information['mode_direction']['drive'], carpark = information['carpark'])
    elif mode_selected == 'transit':
        plot = display_map(information['mode_direction']['transit'])
    elif mode_selected == 'cycle':
        plot = display_map(information['mode_direction']['cycle'])
    elif mode_selected == 'walk':
        plot = display_map(information['mode_direction']['walk'])
    return plot
