def nz(val, offset=0):
    """ number """
    return 'NULL' if val is None else f"{val + offset}"


def qt(val):
    """ char """
    return 'NULL' if val is None else f"'{val}'"


def dstr(val):
    """ date """
    return 'NULL::date' if val is None else f"'{val.strftime('%Y-%m-%d')}'::date"


def bstr(val):
    """ boolean """
    return 'NULL::boolean' if val is None else 'true' if val is True else 'false'


def astr(val):
    """ array """
    return ('NULL::smallint[]' if val is None else
            "'{%s}'::smallint[]" % ','.join([str(v) for v in val]))


class Replicate:
    """ Given a farm year, return a str of SQL which can reproduce it. """
    def __init__(self, fy, user_id, live_to_loc):
        self.fy = fy
        self.user_id = user_id
        self.live_to_loc = live_to_loc
        self.fy_dict = get_fy_dict(fy, user_id, live_to_loc)

    def replicate(self):
        sql = f"""
WITH newfarmyear (
  farm_name, county_code, crop_year, cropland_acres_owned,
  variable_rented_acres, cash_rented_acres, var_rent_cap_floor_frac,
  annual_land_int_expense, annual_land_principal_pmt, property_taxes,
  land_repairs, eligible_persons_for_cap, state_id, user_id,
  is_model_run_date_manual, other_nongrain_expense,
  other_nongrain_income, manual_model_run_date,
  basis_increment, est_sequest_frac, first_date
) AS (
  VALUES
  {self.get_fy_vals()}
),
insertedfarmyear (
  farm_year_id
) AS (
  INSERT INTO public.main_farmyear(
  farm_name, county_code, crop_year, cropland_acres_owned,
  variable_rented_acres, cash_rented_acres, var_rent_cap_floor_frac,
  annual_land_int_expense, annual_land_principal_pmt, property_taxes,
  land_repairs, eligible_persons_for_cap, state_id, user_id,
  is_model_run_date_manual, other_nongrain_expense,
  other_nongrain_income, manual_model_run_date,
  basis_increment, est_sequest_frac, first_date)
  SELECT
  farm_name, county_code, crop_year, cropland_acres_owned,
  variable_rented_acres, cash_rented_acres, var_rent_cap_floor_frac,
  annual_land_int_expense, annual_land_principal_pmt, property_taxes,
  land_repairs, eligible_persons_for_cap, state_id, user_id,
  is_model_run_date_manual, other_nongrain_expense,
  other_nongrain_income, manual_model_run_date,
  basis_increment, est_sequest_frac, first_date
  FROM newfarmyear
  RETURNING id as farm_year_id
),
newfsacrops (
  plc_base_acres, arcco_base_acres, plc_yield,
  fsa_crop_type_id, effective_ref_price, natl_loan_rate
) AS (
  VALUES
  {self.get_fsc_vals()}
),
insertedfsacrops (
  farm_year_id, fsa_crop_id, fsa_crop_type_id
) AS (
  INSERT INTO public.main_fsacrop(
  farm_year_id, plc_base_acres, arcco_base_acres, plc_yield,
  fsa_crop_type_id, effective_ref_price, natl_loan_rate)
  SELECT (
    SELECT insertedfarmyear.farm_year_id
    FROM insertedfarmyear
  ),
  n1.plc_base_acres, n1.arcco_base_acres, n1.plc_yield, n1.fsa_crop_type_id,
  n1.effective_ref_price::double precision, n1.natl_loan_rate::double precision
  FROM newfsacrops n1
  RETURNING farm_year_id, id as fsa_crop_id, fsa_crop_type_id
),
newmarketcrops (
  fsa_crop_type_id, assumed_basis_for_new,
  market_crop_type_id, price_factor
) AS (
  VALUES
  {self.get_mc_vals()}
),
insertedmarketcrops (
  market_crop_id, farm_year_id, market_crop_type_id
) AS (
  INSERT INTO public.main_marketcrop(
  fsa_crop_id, farm_year_id, assumed_basis_for_new,
  market_crop_type_id, price_factor)
  SELECT
  ifsc.fsa_crop_id, ifsc.farm_year_id, n2.assumed_basis_for_new,
  n2.market_crop_type_id, n2.price_factor
  FROM newmarketcrops n2 INNER JOIN insertedfsacrops ifsc
  ON n2.fsa_crop_type_id = ifsc.fsa_crop_type_id
  RETURNING id as market_crop_id, farm_year_id, market_crop_type_id
),
"""

        if self.get_ct_vals() != '':
            sql += """
newcontracts (
  market_crop_type_id, contract_date, bushels, terminal, contract_number,
  delivery_start_date, delivery_end_date, basis_price, futures_price
) AS (
  VALUES
  {self.get_ct_vals()}
),
insertedcontracts (
  id
) AS (
  INSERT INTO public.main_contract(
  market_crop_id, contract_date, bushels, terminal, contract_number,
  delivery_start_date, delivery_end_date, basis_price, futures_price)
  SELECT
  imc.market_crop_id, n3.contract_date::date, n3.bushels, n3.terminal,
  n3.contract_number, n3.delivery_start_date::date,
  n3.delivery_end_date::date, n3.basis_price::double precision,
  n3.futures_price::double precision
  FROM newcontracts n3 inner join insertedmarketcrops imc
  ON n3.market_crop_type_id = imc.market_crop_type_id
  RETURNING id
),
"""

        sql += """
newfarmcrops (
  market_crop_type_id, planted_acres, ta_aph_yield, adj_yield,
  rate_yield, ye_use, ta_use, subcounty, coverage_type,
  product_type, base_coverage_level, sco_use,
  eco_level, prot_factor, ins_practice, ins_practices,
  farm_crop_type_id, ins_crop_type_id,
  cty_yield_final, harv_price_disc_end,
  proj_price_disc_end, harv_price_disc_start,
  proj_price_disc_start
) AS (
  VALUES
  {self.get_fc_vals()}
),
insertedfarmcrops (
  farm_year_id, farm_crop_id, farm_crop_type_id
  ) AS (
  INSERT INTO public.main_farmcrop(
  market_crop_id, farm_year_id, planted_acres, ta_aph_yield, adj_yield,
  rate_yield, ye_use, ta_use, subcounty, coverage_type,
  product_type, base_coverage_level, sco_use,
  eco_level, prot_factor, ins_practice, ins_practices,
  farm_crop_type_id, ins_crop_type_id,
  cty_yield_final, harv_price_disc_end,
  proj_price_disc_end, harv_price_disc_start,
  proj_price_disc_start)
  SELECT
  imc.market_crop_id, imc.farm_year_id, n4.planted_acres, n4.ta_aph_yield,
  n4.adj_yield, n4.rate_yield, n4.ye_use, n4.ta_use, n4.subcounty,
  n4.coverage_type::smallint, n4.product_type::smallint,
  n4.base_coverage_level::double precision, n4.sco_use,
  n4.eco_level::double precision, n4.prot_factor, n4.ins_practice,
  n4.ins_practices::smallint[], n4.farm_crop_type_id, n4.ins_crop_type_id,
  n4.cty_yield_final::date, n4.harv_price_disc_end::date,
  n4.proj_price_disc_end::date, n4.harv_price_disc_start::date,
  n4.proj_price_disc_start::date
  FROM newfarmcrops n4 inner join insertedmarketcrops imc
  ON n4.market_crop_type_id = imc.market_crop_type_id
  RETURNING farm_year_id, id as farm_crop_id, farm_crop_type_id
),
"""
        if self.get_fbc_vals() != '':
            sql += """
newfbcs (
  farm_yield, county_yield,
  yield_variability, other_gov_pmts,
  other_revenue, fertilizers, pesticides, seed, drying,
  storage, other_direct_costs, machine_hire_lease, utilities,
  machine_repair, fuel_and_oil, light_vehicle, machine_depr,
  labor_and_mgmt, building_repair_and_rent, building_depr,
  insurance, misc_overhead_costs, interest_nonland,
  other_overhead_costs, rented_land_costs, budget_id,
  description, state_id, farm_crop_type_id, is_irr,
  is_rot, budget_crop_id, budget_date,
  baseline_yield_for_var_rent, is_farm_yield_final,
  yield_factor, are_costs_final
) AS (
  VALUES
  {self.get_fbc_vals()}
),
insertedfbcs AS (
  INSERT INTO public.main_farmbudgetcrop(
  farm_crop_id, farm_year_id, farm_yield, county_yield,
  yield_variability, other_gov_pmts,
  other_revenue, fertilizers, pesticides, seed, drying,
  storage, other_direct_costs, machine_hire_lease, utilities,
  machine_repair, fuel_and_oil, light_vehicle, machine_depr,
  labor_and_mgmt, building_repair_and_rent, building_depr,
  insurance, misc_overhead_costs, interest_nonland,
  other_overhead_costs, rented_land_costs, budget_id,
  description, state_id, farm_crop_type_id, is_irr,
  is_rot, budget_crop_id, budget_date,
  baseline_yield_for_var_rent, is_farm_yield_final,
  yield_factor, are_costs_final)
  SELECT
  ifc.farm_crop_id, ifc.farm_year_id, n5.farm_yield, n5.county_yield,
  n5.yield_variability, n5.other_gov_pmts,
  n5.other_revenue, n5.fertilizers, n5.pesticides, n5.seed, n5.drying,
  n5.storage, n5.other_direct_costs, n5.machine_hire_lease, n5.utilities,
  n5.machine_repair, n5.fuel_and_oil, n5.light_vehicle, n5.machine_depr,
  n5.labor_and_mgmt, n5.building_repair_and_rent, n5.building_depr,
  n5.insurance, n5.misc_overhead_costs, n5.interest_nonland,
  n5.other_overhead_costs, n5.rented_land_costs, n5.budget_id,
  n5.description, n5.state_id, n5.farm_crop_type_id, n5.is_irr,
  n5.is_rot, n5.budget_crop_id, n5.budget_date,
  n5.baseline_yield_for_var_rent, n5.is_farm_yield_final,
  n5.yield_factor, n5.are_costs_final
  FROM newfbcs n5 inner join insertedfarmcrops ifc
  ON n5.farm_crop_type_id = ifc.farm_crop_type_id
  RETURNING *
)
"""
        sql += """
select * FROM insertedfbcs LIMIT 1;
"""
        return sql

    def get_fy_vals(self):
        return '(' + ', '.join(str(v) for v in self.fy_dict['values']) + ')'

    def get_fsc_vals(self):
        vals = []
        for d in self.fy_dict['fsa_crops']:
            vals.append('(' + ', '.join(str(v) for v in d['values']) + ')')
        return ',\n'.join(vals)

    def get_mc_vals(self):
        vals = []
        for d0 in self.fy_dict['fsa_crops']:
            for d in d0['market_crops']:
                vals.append('(' + ', '.join(str(v) for v in d['values']) + ')')
        return ',\n'.join(vals)

    def get_ct_vals(self):
        vals = []
        for d0 in self.fy_dict['fsa_crops']:
            for d1 in d0['market_crops']:
                for d in d1['contracts']:
                    vals.append('(' + ', '.join(str(v) for v in d['values']) + ')')
        return ',\n'.join(vals)

    def get_fc_vals(self):
        vals = []
        for d0 in self.fy_dict['fsa_crops']:
            for d1 in d0['market_crops']:
                for d in d1['farm_crops']:
                    vals.append('(' + ', '.join(str(v) for v in d['values']) + ')')
        return ',\n'.join(vals)

    def get_fbc_vals(self):
        vals = []
        for d0 in self.fy_dict['fsa_crops']:
            for d1 in d0['market_crops']:
                for d2 in d1['farm_crops']:
                    if 'fbcs' in d2:
                        for d in d2['fbcs']:
                            vals.append('(' + ', '.join(str(v) for v in
                                                        d['values']) + ')')
        return ',\n'.join(vals)


def get_fy_dict(fy, user_id, live_to_loc):
    fy_dict = {
        'values': [
            qt(fy.farm_name), fy.county_code, fy.crop_year,
            fy.cropland_acres_owned, fy.variable_rented_acres,
            fy.cash_rented_acres, fy.var_rent_cap_floor_frac,
            fy.annual_land_int_expense, fy.annual_land_principal_pmt,
            fy.property_taxes, fy.land_repairs,
            fy.eligible_persons_for_cap, fy.state_id, user_id,
            bstr(fy.is_model_run_date_manual), fy.other_nongrain_expense,
            fy.other_nongrain_income, dstr(fy.manual_model_run_date),
            fy.basis_increment, fy.est_sequest_frac, dstr(fy.first_date)
        ],
        'fsa_crops': []
    }
    for fa in fy.fsa_crops.all():
        fa_dict = {
            'values': [
                fa.plc_base_acres, fa.arcco_base_acres, fa.plc_yield,
                fa.fsa_crop_type_id, nz(fa.effective_ref_price),
                nz(fa.natl_loan_rate)],
            'market_crops': []}

        for mc in fa.market_crops.all():
            mc_dict = {
                'values': [
                     fa.fsa_crop_type_id, mc.assumed_basis_for_new,
                     mc.market_crop_type_id, mc.price_factor],
                'farm_crops': [],
                'contracts': []}

            for ct in mc.contracts.all():
                ct_dict = {
                    'values': [
                        mc.market_crop_type_id, dstr(ct.contract_date),
                        nz(ct.bushels), qt(ct.terminal), qt(ct.contract_number),
                        dstr(ct.delivery_start_date), dstr(ct.delivery_end_date),
                        nz(ct.basis_price), nz(ct.futures_price)]}
                mc_dict['contracts'].append(ct_dict)

            for fc in mc.farm_crops.all():
                fc_dict = {
                    'values': [
                        mc.market_crop_type_id, fc.planted_acres,
                        fc.ta_aph_yield, fc.adj_yield, fc.rate_yield,
                        bstr(fc.ye_use), bstr(fc.ta_use), qt(fc.subcounty),
                        nz(fc.coverage_type), nz(fc.product_type),
                        nz(fc.base_coverage_level), bstr(fc.sco_use),
                        nz(fc.eco_level), fc.prot_factor, fc.ins_practice,
                        astr(fc.ins_practices), fc.farm_crop_type_id,
                        fc.ins_crop_type_id, dstr(fc.cty_yield_final),
                        dstr(fc.harv_price_disc_end), dstr(fc.proj_price_disc_end),
                        dstr(fc.harv_price_disc_start), dstr(fc.proj_price_disc_start),
                    ],
                    'fbcs': []}

                if fc.has_budget():
                    bc = fc.farmbudgetcrop
                    bc_dict = {
                        'values': [
                            bc.farm_yield,
                            bc.county_yield, bc.yield_variability,
                            bc.other_gov_pmts, bc.other_revenue,
                            bc.fertilizers, bc.pesticides, bc.seed,
                            bc.drying, bc.storage, bc.other_direct_costs,
                            bc.machine_hire_lease, bc.utilities,
                            bc.machine_repair, bc.fuel_and_oil,
                            bc.light_vehicle, bc.machine_depr,
                            bc.labor_and_mgmt, bc.building_repair_and_rent,
                            bc.building_depr, bc.insurance,
                            bc.misc_overhead_costs, bc.interest_nonland,
                            bc.other_overhead_costs, bc.rented_land_costs,
                            nz(bc.budget_id, offset=(3 if live_to_loc else 0)),
                            qt(bc.description), bc.state_id,
                            nz(bc.farm_crop_type_id), bstr(bc.is_irr), bstr(bc.is_rot),
                            nz(bc.budget_crop_id, offset=(63 if live_to_loc else 0)),
                            dstr(bc.budget_date), bc.baseline_yield_for_var_rent,
                            bstr(bc.is_farm_yield_final), bc.yield_factor,
                            bstr(bc.are_costs_final)]}
                    fc_dict['fbcs'].append(bc_dict)
                mc_dict['farm_crops'].append(fc_dict)
            fa_dict['market_crops'].append(mc_dict)
        fy_dict['fsa_crops'].append(fa_dict)
    return fy_dict
