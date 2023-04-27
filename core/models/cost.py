"""
Module cost

Contains a single class, Cost, which loads its data
for a given crop year when an instance is created.
"""
from core.models.analysis import Analysis
from core.models.crop_ins import CropIns
from core.models.revenue import Revenue
from core.models.util import crop_in, SEASON_CROPS


class Cost(Analysis):
    """
    Computes total estimated cost for the farm crop year
    corresponding to an arbitrary sensitivity factor for yield.

    Sample usage in a python or ipython console:
      from ifbt import Cost, Premium
      c = Cost(2023, prem=Premium())
      c.total_cost()
    """
    DATA_FILES = 'farm_data cost_data'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crop_ins = CropIns(self.crop_year)
        self.revenue = Revenue(self.crop_year)

    @crop_in(*SEASON_CROPS)
    def total_direct_cost_crop(self, crop):
        return (
            self.fertilizers[crop] +
            self.pesticides[crop] +
            self.seed[crop] +
            self.drying[crop] +
            self.storage[crop] +
            self.crop_ins.total_premium_per_acre_crop(crop) +
            self.other_direct_cost[crop]) * self.acres[crop]

    # Row totals
    def total_fertilizers(self):
        return sum((self.fertilizers[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_pesticides(self):
        return sum((self.pesticides[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_seed(self):
        return sum((self.seed[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_drying(self):
        return sum((self.drying[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_storage(self):
        return sum((self.storage[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_crop_ins(self):
        return self.crop_ins.total_premium()

    def total_other_direct_cost(self):
        return sum((self.other_direct_cost[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_direct_cost(self):
        return sum((self.total_direct_cost_crop(crop) for crop in
                   (SEASON_CROPS))) + self.other_nongrain_direct_cost

    @crop_in(*SEASON_CROPS)
    def total_power_cost_crop(self, crop):
        return (self.machinery[crop] +
                self.utilities[crop] +
                self.machine_repair[crop] +
                self.fuel[crop] +
                self.light_vehicle[crop] +
                self.machine_depr[crop]) * self.acres[crop]

    # Row totals
    def total_machinery(self):
        return sum((self.machinery[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_utilities(self):
        return sum((self.utilities[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_machine_repair(self):
        return sum((self.machine_repair[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_fuel(self):
        return sum((self.fuel[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_light_vehicle(self):
        return sum((self.light_vehicle[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_machine_depr(self):
        return sum((self.machine_depr[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_power_cost(self):
        return sum((self.total_power_cost_crop(crop) for crop in
                   (SEASON_CROPS))) + self.other_nongrain_power_cost

    @crop_in(*SEASON_CROPS)
    def total_overhead_cost_crop(self, crop):
        return (self.hired_labor[crop] +
                self.building_rent[crop] +
                self.building_depr[crop] +
                self.insurance[crop] +
                self.misc_overhead_cost[crop] +
                self.interest_nonland[crop] +
                self.other_overhead_cost[crop]) * self.acres[crop]

    # Row totals
    def total_hired_labor(self):
        return sum((self.hired_labor[crop] * self.acres[crop] for crop in SEASON_CROPS))

    def total_building_rent(self):
        return sum((self.building_rent[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_building_depr(self):
        return sum((self.building_depr[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_insurance(self):
        return sum((self.insurance[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_misc_overhead_cost(self):
        return sum((self.misc_overhead_cost[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_interest(self):
        return sum((self.interest[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_other_overhead_cost(self):
        return sum((self.other_overhead_cost[crop] * self.acres[crop]
                    for crop in SEASON_CROPS))

    def total_overhead_cost(self):
        return sum((self.total_overhead_cost_crop(crop)
                    for crop in SEASON_CROPS)) + self.other_nongrain_ovhd_expense

    @crop_in(*SEASON_CROPS)
    def total_non_land_cost_crop(self, crop):
        return (
            self.total_direct_cost_crop(crop) +
            self.total_power_cost_crop(crop) +
            self.total_overhead_cost_crop(crop))

    def total_non_land_cost(self, yf=1):
        return (self.total_direct_cost() +
                self.total_power_cost() +
                self.total_overhead_cost())

    @crop_in(*SEASON_CROPS)
    def operator_and_land_return_crop(self, crop, pf=1, yf=1):
        return (self.revenue.gross_revenue_crop(crop, pf, yf) -
                self.total_non_land_cost_crop(crop))

    def total_operator_and_land_return(self, pf=1, yf=1):
        return sum((self.operator_and_land_return_crop(crop, pf, yf)
                    for crop in SEASON_CROPS))

    @crop_in(*SEASON_CROPS)
    def rented_land_cost_crop(self, crop):
        return self.rented_land_cost * self.acres[crop]/self.total_planted_acres()

    def total_rented_land_cost(self):
        return self.rented_land_cost

    @crop_in(*SEASON_CROPS)
    def owned_land_cost_crop(self, crop):
        return (self.total_owned_land_cost() * self.crop_acres_owned *
                self.acres[crop]/self.total_planted_acres())

    def total_owned_land_cost(self):
        return (self.annual_land_interest_exp + self.annual_land_principal_pmts +
                self.property_taxes + self.land_repairs)

    @crop_in(*SEASON_CROPS)
    def total_land_cost_crop(self, crop):
        return (self.rented_land_cost_crop(crop) +
                self.owned_land_cost_crop(crop))

    def total_land_cost(self):
        return (sum((self.total_land_cost_crop(crop) for crop in SEASON_CROPS))
                + self.other_nongrain_land_cost)

    @crop_in(*SEASON_CROPS)
    def total_cost_crop(self, crop):
        return (self.total_non_land_cost_crop(crop) +
                self.total_land_cost_crop(crop))

    def total_nongrain_cost(self):
        return (self.other_nongrain_direct_cost +
                self.other_nongrain_power_cost +
                self.other_nongrain_ovhd_expense +
                self.other_nongrain_land_cost)

    def total_cost(self):
        return sum((self.total_cost_crop(crop) for crop in SEASON_CROPS))
