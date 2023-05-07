from django.contrib import admin

from .models import (State, County, InsCrop, InsCropType, InsPractice, Subcounty)

admin.site.register(State)
admin.site.register(County)
admin.site.register(InsCrop)
admin.site.register(InsCropType)
admin.site.register(InsPractice)
admin.site.register(Subcounty)
