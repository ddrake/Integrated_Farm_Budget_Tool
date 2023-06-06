from django.test import TestCase

from .models.farm_year import FarmYear
from django.contrib.auth.models import User


class FarmYearTestCase(TestCase):
    def setUp(self):
        joe = User.objects.create(username='joe124', password='verrysekrit')
        self.farm_year = FarmYear.objects.create(user=joe, farm_name="Joey's farm",
                                                 state_id=5, county_code=1)

    def test_farm_year(self):
        self.assertEqual(self.farm_year.farm_crops.count(), 4)

    def test_farm_crop_types(self):
        for fc in self.farm_year.farm_crops.all():
            self.assertIn(fc.farm_crop_type_id, (1, 2, 3, 5))
