from django.shortcuts import render, redirect
from api.views import *
import pandas as pd
import folium
import googlemaps
import polyline
import re
import time


fileObject = open("apikey.txt", "r")
api_key = fileObject.read()
directions = googlemaps.Client(key=api_key)


def nearby_restaurants(place_coord):
    places_result = directions.places_nearby(place_coord, 500, type='restaurant', rank_by='prominence')

    restaurants_list = []
    for place in sorted(places_result['results'], key=lambda x: x.get('rating', 0), reverse=True)[:10]:
        restaurant = {}
        if 'rating' in place:
            restaurant['rating'] = place['rating']
        else:
            restaurant['rating'] = None
        restaurant['name'] = place.get('name', '')
        restaurants_list.append(restaurant)
    return restaurants_list


def locations(request):
    if request.method == 'POST':
        start = request.POST.get('start')
        end = request.POST.get('end')
        mode = ''
        if request.POST.get('mode_select') == 'Drive':
            mode = 'driving'
        elif request.POST.get('mode_select') == 'Taxi':
            mode = 'driving'
        elif request.POST.get('mode_select') == 'Public Transport':
            mode = 'transit'
        elif request.POST.get('mode_select') == 'Bicycle':
            mode = 'bicycling'
        elif request.POST.get('mode_select') == 'Walk':
            mode = 'walking'
        return redirect('get_direction', start=start, end=end, mode=mode)
    else:
        return render(request, 'route.html')


timing = -7201
if 'df_weather_forecast' not in locals():
    df_weather_forecast = get_weather_forecast()
    timing = time.time()
elif time.time() - timing >= (2 * 60 * 60):
    df_weather_forecast = get_weather_forecast()
    timing = time.time()


def get_direction(request):
    mode_select = request.GET.get('mode_select')
    start_location = request.GET.get('start')  # could be either address or postal code
    end_location = request.GET.get('end')
    mode = ''
    if mode_select == 'Drive':
        mode = 'driving'
    elif mode_select == 'Taxi':
        mode = 'driving'
    elif mode_select == 'Public Transport':
        mode = 'transit'
    elif mode_select == 'Bicycle':
        mode = 'bicycling'
    elif mode_select == 'Walk':
        mode = 'walking'

    if start_location.isdigit():
        nomi = pgeocode.Nominatim('sg')
        place = nomi.query_postal_code(start_location)
        place_lat = place['latitude']
        place_long = place['longitude']
        start = (place_lat, place_long)
    else:
        loc = Nominatim(user_agent="GetLoc")
        getLoc = loc.geocode(start_location)
        place_lat = getLoc.latitude
        place_long = getLoc.longitude
        start = (place_lat, place_long)

    if end_location.isdigit():
        nomi = pgeocode.Nominatim('sg')
        place = nomi.query_postal_code(end_location)
        place_lat = place['latitude']
        place_long = place['longitude']
        end = (place_lat, place_long)
    else:
        loc = Nominatim(user_agent="GetLoc")
        getLoc = loc.geocode(end_location)
        place_lat = getLoc.latitude
        place_long = getLoc.longitude
        end = (place_lat, place_long)

    direction = directions.directions(start, end, mode)

    methods = ['walking', 'driving', 'transit', 'bicycling']
    durations = {}

    for method in methods:
        result = directions.directions(start, end, mode=method)
        duration = result[0]['legs'][0]['duration']['text']
        hours = 0
        minutes = 0
        match = re.search(r'(\d+)\s*hours?', duration)
        if match:
            hours = int(match.group(1))
        match = re.search(r'(\d+)\s*mins?', duration)
        if match:
            minutes = int(match.group(1))
        duration_mins = hours * 60 + minutes
        durations[method] = duration_mins
    min_duration = min(durations.values())

    if min_duration == durations['walking']:
        durations['walking'] = str(durations['walking']) + " mins (fastest mode)"
    else:
        durations['walking'] = str(durations['walking']) + " mins"
    if min_duration == durations['driving']:
        durations['driving'] = str(durations['driving']) + " mins (fastest mode)"
    else:
        durations['driving'] = str(durations['driving']) + " mins"
    if min_duration == durations['bicycling']:
        durations['bicycling'] = str(durations['bicycling']) + " mins (fastest Mmode)"
    else:
        durations['bicycling'] = str(durations['bicycling']) + " mins"
    if min_duration == durations['transit']:
        durations['transit'] = str(durations['transit']) + " mins (fastest mode)"
    else:
        durations['transit'] = str(durations['transit']) + " mins"

    # steps - output: formatted_directions
    steps = direction[0]['legs'][0]['steps']
    formatted_steps = []
    for i, step in enumerate(steps):
        distance = step['distance']['text']
        duration = step['duration']['text']
        instruction = re.sub('<.*?>', '', step['html_instructions'])
        formatted_step = f"{distance} ({duration}): {instruction}"
        formatted_step = formatted_step.replace("&nbsp;", " ")
        if i == len(steps) - 1:
            formatted_step += "\nDestination will be on the left"
        formatted_steps.append(formatted_step)
    formatted_directions = "\n".join(formatted_steps)

    # carpark - output: formatted_availability
    df_hdb_cp = carpark_init()
    carpark_latlog, carpark_num_list = nearest_carpark(end, 300, df_hdb_cp)
    carpark = pd.DataFrame({'carpark_list': carpark_latlog, 'carpark_latlog': carpark_num_list})
    availability = hdb_carpark_availability(carpark_num_list)
    availability_dict = {cp: avail for cp, avail in availability.items()}
    formatted_availability = "\n".join(
        [f"Carpark {cp}: {avail} lots available" for cp, avail in availability_dict.items()])

    restaurants_list = nearby_restaurants(end)

    # taxi - output: num_taxi
    num_taxi_all_singapore, num_taxi_near_me, taxi_near = taxi_availability(start, 500)
    num_taxi = str(num_taxi_near_me) + " taxis available"

    # weather forecast
    start_weather_forecast, dest_weather_forecast = trip_weather_forecast(df_weather_forecast, start, end)

    if (mode_select == 'Walk' or mode_select == 'Bicycle') and \
            ('Cloudy' in start_weather_forecast or 'Cloudy' in dest_weather_forecast):
        concerns = mode_select + " - Cloudy weather"
    elif (mode_select == 'Walk' or mode_select == 'Bicycle') and \
            ('showers' in start_weather_forecast or 'showers' in dest_weather_forecast):
        concerns = mode_select + " - Rainy weather"
    elif mode_select == 'Taxi' and num_taxi_near_me == 0:
        concerns = mode_select + " - No taxi available nearby"
    elif mode_select == 'Taxi' and num_taxi_near_me < 5:
        concerns = mode_select + " - Low taxi availability nearby"
    elif mode_select == 'Drive' and 'No HDB carpark' in formatted_availability:
        concerns = mode_select + " - No HDB carpark lots available nearby"
    else:
        concerns = 'None'

    plot_html = ""
    if mode == 'driving':
        plot_html = display_map(directions.directions(start, end, mode='driving')[0]['legs'][0]['steps'],
                                carpark=carpark)
    elif mode == 'transit':
        plot_html = display_map(directions.directions(start, end, mode='transit')[0]['legs'][0]['steps'])
    elif mode == 'bicycling':
        plot_html = display_map(directions.directions(start, end, mode='bicycling')[0]['legs'][0]['steps'])
    elif mode == 'walking':
        plot_html = display_map(directions.directions(start, end, mode='walking')[0]['legs'][0]['steps'])

    result = {
        'mode_select': mode_select,
        'mode': mode,
        'start_location': start_location,
        'end_location': end_location,
        'duration': direction[0]['legs'][0]['duration']['text'],
        'walk': durations['walking'],
        'drive': durations['driving'],
        'taxi': durations['driving'],
        'transit': durations['transit'],
        'cycle': durations['bicycling'],
        'distance': direction[0]['legs'][0]['distance']['text'],
        'directions': direction[0]['legs'][0]['steps'],
        'plot_html': plot_html,
        'steps': formatted_directions,
        'carpark': formatted_availability,
        'num_taxi': num_taxi,
        'concerns': concerns,
        'start_weather_forecast': start_weather_forecast,
        'dest_weather_forecast': dest_weather_forecast,
        'restaurants_list': restaurants_list
    }

    context = {
        "start": start,
        "end": end,
        "mode": mode,
        "google_api_key": api_key,
        "result": result,
    }
    return render(request, 'results.html', context)


def display_map(directions, taxi=[], carpark=pd.DataFrame({'carpark_list': [],
                                                           'carpark_latlog': [], 'availability': []})):
    colours = {'WALKING': 'blue', 'DRIVING': 'green', 'TRANSIT': 'green', 'BICYCLING': 'purple'}
    display = folium.Map()
    lower = []
    upper = []

    for i in taxi:
        folium.Marker([i[1], i[0]], icon=folium.Icon(color="orange", prefix='fa', icon="taxi")).add_to(display)
        lower.append([i[1], i[0]])
        upper.append([i[1], i[0]])

    for i in range(len(carpark)):
        folium.Marker(carpark['carpark_latlog'][i], icon=folium.Icon(color="green", prefix='fa', icon="car"),
                      tooltip='Available Lots: ' + str(carpark['availability'][i])).add_to(display)
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
        elif i == len(routes) - 1:
            folium.Marker(routes[i][-1], icon=folium.Icon(color="red", prefix='fa', icon="flag")).add_to(display)

        folium.PolyLine(routes[i], color=colours[travel_mode[i]], weight=5).add_to(display)

        lower.append(pd.DataFrame(routes[i]).min().values.tolist())
        upper.append(pd.DataFrame(routes[i]).max().values.tolist())

    sw = (pd.DataFrame(lower).min()).values.tolist()
    ne = (pd.DataFrame(upper).max()).values.tolist()
    display.fit_bounds([sw, ne])
    map_html = display._repr_html_()
    return map_html
