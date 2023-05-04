from django.contrib import admin

from .models import (State, County, Crop, CropType, Practice, Subcounty)

admin.site.register(State)
admin.site.register(County)
admin.site.register(Crop)
admin.site.register(CropType)
admin.site.register(Practice)
admin.site.register(Subcounty)
