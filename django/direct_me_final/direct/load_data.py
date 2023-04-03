import csv
from direct.models import CarPark

def load_data():
    with open('hdb-carpark-information.csv') as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            CarPark.objects.create(
                car_park_no=row[0],
                address=row[1],
                x_coord=row[2],
                y_coord=row[3],
                free_parking=row[4],
            )
