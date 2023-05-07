from django.contrib import admin

from .models import (Budget, FarmYear, FsaCropType, MarketCropType, FarmCropType,
                     BudgetCropType, FuturesPrice, FsaCrop, MarketCrop,
                     FarmCrop, BudgetCrop)

admin.site.register(Budget)
admin.site.register(FarmYear)
admin.site.register(MarketCropType)
admin.site.register(FsaCropType)
admin.site.register(FarmCropType)
admin.site.register(BudgetCropType)
admin.site.register(FuturesPrice)
admin.site.register(FsaCrop)
admin.site.register(MarketCrop)
admin.site.register(FarmCrop)
admin.site.register(BudgetCrop)
