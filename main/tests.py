from django.test import TestCase

from .models import FarmYear
from django.contrib.auth.models import User


class FarmYearTestCase(TestCase):
    def setUp(self):
        joe = User.objects.create(username='joe124', password='verrysekrit')
        self.farm_year = FarmYear.objects.create(user=joe, farm_name="Joey's farm",
                                                 state_id=5, county_code=1)

    def test_farm_year(self):
        self.assertEqual(self.farm_year.farm_crops.count(), 2)
