from django.db import models


class CarPark(models.Model):
    objects = None
    car_park_no = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    x_coord = models.DecimalField(max_digits=40, decimal_places=20)
    y_coord = models.DecimalField(max_digits=40, decimal_places=20)
    free_parking = models.CharField(max_length=10)
