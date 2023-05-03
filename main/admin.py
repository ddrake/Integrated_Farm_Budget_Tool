from django.contrib import admin

from .models import (Budget, FarmYear, PricedCropType, FarmCropType, BudgetCropType,
                     HarvestFuturesPrice, PricedCrop, FarmCrop, BudgetCrop)

admin.site.register(Budget)
admin.site.register(FarmYear)
admin.site.register(PricedCropType)
admin.site.register(FarmCropType)
admin.site.register(BudgetCropType)
admin.site.register(HarvestFuturesPrice)
admin.site.register(PricedCrop)
admin.site.register(FarmCrop)
admin.site.register(BudgetCrop)
