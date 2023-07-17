from .farm_year import FarmYear
from .market_crop import MarketCrop


class KeyData(object):
    def __init__(self, farm_year_id, for_sens_table=False):
        """
        In the context of the sensitivity table, data related to global yield and price
        factors would be confusing so we customize based on for_sens_table.
        """
        self.farm_year = FarmYear.objects.get(pk=farm_year_id)
        self.for_sens_table = for_sens_table
        self.model_run = self.farm_year.get_model_run_date()
        self.farm_crops = [fc for fc in self.farm_year.farm_crops
                           .filter(planted_acres__gt=0).all() if fc.has_budget()]
        self.market_crop_ids = {fc.market_crop_id: fc for fc in self.farm_crops}.keys()
        self.market_crops = [MarketCrop.objects.get(pk=pk)
                             for pk in self.market_crop_ids]
        self.market_crops_all = list(MarketCrop.objects.
                                     filter(farm_year=farm_year_id).all())
        self.fsa_crops = [fsc for fsc in self.farm_year.fsa_crops.all()]
        self.farm_crop_names = [
            str(fc.farm_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for fc in self.farm_crops]
        self.market_crop_names = [
            str(mc.market_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for mc in self.market_crops]
        self.market_crop_names_all = [
            str(mc.market_crop_type).replace('Winter', 'W').replace('Spring', 'S')
            for mc in self.market_crops_all]

    def get_tables(self):
        if len(self.farm_crops) == 0:
            return {}
        return {
            'cropins': self.crop_ins_table(),
            'yield': self.yield_table(),
            'title': self.title_table(),
            'futctr': self.fut_contract_table(),
            'price': self.market_price_table(),
            'modelrun': self.model_run_table(),
        }

    def crop_ins_table(self):
        """
        Show crop insurance selections for each crop and costs in ($000) with total
        """
        base_policies = [
            (fc.coverage_type, fc.product_type, fc.base_coverage_level)
            for fc in self.farm_crops]
        options = [(fc.sco_use, fc.eco_level) for fc in self.farm_crops]
        ci_info = [fc.get_selected_premiums() for fc in self.farm_crops]
        baselabels = []
        scolabels = []
        ecolabels = []
        basecost = 0
        scocost = 0
        ecocost = 0
        for i, ci in enumerate(ci_info):
            ct, pt, cl = base_policies[i]
            ctname = 'Farm' if ct == 1 else 'County' if ct == 0 else 'None'
            ptname = ('RP' if pt == 0 else 'RP-HPE' if pt == 1 else
                      'YP' if pt == 2 else 'None')
            baselvl = 'None' if cl is None else f'{cl:.0%}'
            baselabels.append('None' if ct is None or pt is None or cl is None
                              else f'{ctname} {ptname} {baselvl}')
            scolabels.append('SCO 86%' if options[i][0] else 'No SCO')
            ecolabels.append(f'ECO {options[i][1]:.0%}'
                             if options[i][1] is not None else 'No ECO')
            acres = self.farm_crops[i].planted_acres
            basecost += ci['base'] * acres
            scocost += ci['sco'] * acres
            ecocost += ci['eco'] * acres
        allcosts = [basecost, scocost, ecocost]
        allcosts.append(sum(allcosts))
        costs = [f'${c / 1000:.0f}' for c in allcosts]

        rows = []
        rows.append(('Crop Insurance', []))
        rows.append(('', self.farm_crop_names + ['$000']))
        rows.append(('Base Policy', baselabels + [costs[0]]))
        rows.append(('SCO', scolabels + [costs[1]]))
        rows.append(('ECO', ecolabels + [costs[2]]))
        rows.append(('Total', [''] * len(baselabels) + [costs[3]]))
        colspan = len(baselabels) + 2
        return {'rows': rows, 'colspan': colspan}

    def yield_table(self):
        """
        Show yield factor, actual yields
        """
        info = [(fc.farmbudgetcrop.yield_factor, fc.sens_farm_expected_yield(yf=1),
                 fc.sens_farm_expected_yield(), fc.sens_cty_expected_yield(yf=1),
                 fc.sens_cty_expected_yield())
                for fc in self.farm_crops]

        yfs, yields, sensyields, cty, senscty = zip(*info)
        rows = []
        rows.append(('Yields', []))
        rows.append(('', self.farm_crop_names))
        rows.append(('Assumed Farm Yields', [f'{yld:.0f}' for yld in yields]))
        if self.for_sens_table:
            rows.append(('Assumed County Yields', [f'{yld:.0f}' for yld in yields]))
        if not self.for_sens_table:
            rows.append(('Yield Sensitivity Factor', [f'{yf:.0%}' for yf in yfs]))
            rows.append(('Sensitized Farm Yields',
                         [f'{syld:.0f}' for syld in sensyields]))
            rows.append(('Sensitized County Yields',
                         [f'{scty:.0f}' for scty in senscty]))
        colspan = len(yields) + 1
        return {'rows': rows, 'colspan': colspan}

    def title_table(self):
        """
        show PLC acres and ARC-CO acres
        """
        info = [(str(fsc.fsa_crop_type), fsc.plc_base_acres, fsc.arcco_base_acres,
                 fsc.plc_base_acres + fsc.arcco_base_acres,
                 fsc.sens_mya_price(pf=1), fsc.sens_mya_price())
                for fsc in self.fsa_crops]
        cropnames, plc_acres, arcco_acres, tot_acres, myas, smyas = zip(*info)
        rows = []
        rows.append(('Title', []))
        rows.append(('Title Election', cropnames))
        rows.append(('PLC Acres',
                     [f'{0 if tot == 0 else ac/tot:.0%}'
                      for ac, tot in zip(plc_acres, tot_acres)]))
        rows.append(('ARC-CO Acres',
                     [f'{0 if tot == 0 else ac/tot:.0%}'
                      for ac, tot in zip(arcco_acres, tot_acres)]))
        if self.for_sens_table:
            rows.append(('Estimated MYA Price', [f'${mya:.2f}' for mya in myas]))
        else:
            rows.append(('Estimated MYA Price', [f'${mya:.2f}' for mya in smyas]))
        colspan = len(cropnames) + 1
        return {'rows': rows, 'colspan': colspan}

    def fut_contract_table(self):
        """
        Show pct of expected bushels and avg. contract price
        """
        info = ((mc.futures_pct_of_expected(), mc.avg_contract_price)
                for mc in self.market_crops)
        spcts, ctprices = zip(*info)
        rows = []
        rows.append(('Marketed Futures', []))
        rows.append(('', self.market_crop_names))
        rows.append(('% of Expected Bushels', [f'{pct:.0%}' for pct in spcts]))
        rows.append(('Avg. Futures Contract Price', [f'${pr:.2f}' for pr in ctprices]))
        colspan = len(spcts) + 1
        return {'rows': rows, 'colspan': colspan}

    def market_price_table(self):
        """
        Show current harvest futures, price factor, sensitized harvest price, est MYA
        """
        info = [(mc.price_factor, mc.sens_harvest_price(1), mc.sens_harvest_price())
                for mc in self.market_crops_all]
        pfs, prices, sprices = zip(*info)
        rows = []
        rows.append(('Prices', []))
        rows.append(('', self.market_crop_names_all))
        rows.append(('Current Harvest Futures', [f'${p:.2f}' for p in prices]))
        if not self.for_sens_table:
            rows.append(('Price Sensitivity Factor', [f'{p:.0%}' for p in pfs]))
            rows.append(('Assumed Harvest Price', [f'${p:.2f}' for p in sprices]))
        colspan = len(prices) + 1
        return {'rows': rows, 'colspan': colspan}

    def model_run_table(self):
        """
        Show model run date
        """
        mrd = self.farm_year.get_model_run_date().strftime("%m/%d/%Y")
        rows = []
        rows.append(('Model Run Date', [f'{mrd}']))
        return {'rows': rows}
