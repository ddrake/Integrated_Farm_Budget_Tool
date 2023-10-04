# User id for the replica
USER_ID = 1


def nz(val):
    """ number """
    return 'NULL' if val is None else f"{val}"


def qt(val):
    """ char """
    return 'NULL' if val is None else f"'{val}'"


def dstr(val):
    """ date """
    return 'NULL' if val is None else f"'{val.strftime('%Y-%m-%d')}'::date"


def bstr(val):
    """ boolean """
    return 'NULL' if val is None else 'true' if val is True else 'false'


def astr(val):
    """ array """
    return 'NULL' if val is None else "'{%s}'" % ','.join([str(v) for v in val])


def replicate(fy):
    sql = ''

    sql += f"""
INSERT INTO public.main_farmyear(
farm_name, county_code, crop_year, cropland_acres_owned,
variable_rented_acres, cash_rented_acres, var_rent_cap_floor_frac,
annual_land_int_expense, annual_land_principal_pmt, property_taxes,
land_repairs, eligible_persons_for_cap, state_id, user_id,
is_model_run_date_manual, other_nongrain_expense,
other_nongrain_income, manual_model_run_date,
basis_increment, est_sequest_frac)
VALUES (
{qt(fy.farm_name)}, {fy.county_code}, {fy.crop_year}, {fy.cropland_acres_owned},
{fy.variable_rented_acres}, {fy.cash_rented_acres}, {fy.var_rent_cap_floor_frac},
{fy.annual_land_int_expense}, {fy.annual_land_principal_pmt}, {fy.property_taxes},
{fy.land_repairs}, {fy.eligible_persons_for_cap}, {fy.state_id}, {USER_ID},
{bstr(fy.is_model_run_date_manual)}, {fy.other_nongrain_expense},
{fy.other_nongrain_income}, {dstr(fy.manual_model_run_date)},
{fy.basis_increment}, {fy.est_sequest_frac})
returning id;

"""

    for fa in fy.fsa_crops.all():
        sql += f"""
INSERT INTO public.main_fsacrop(
plc_base_acres, arcco_base_acres, plc_yield, farm_year_id,
fsa_crop_type_id, effective_ref_price, natl_loan_rate)
VALUES (
{fa.plc_base_acres}, {fa.arcco_base_acres}, {fa.plc_yield}, farm_year_id,
{fa.fsa_crop_type_id}, {nz(fa.effective_ref_price)}, {nz(fa.natl_loan_rate)})
returning id;

"""

        for mc in fa.market_crops.all():
            sql += f"""
INSERT INTO public.main_marketcrop(
assumed_basis_for_new, farm_year_id, fsa_crop_id,
market_crop_type_id, price_factor)
VALUES (
{mc.assumed_basis_for_new}, farm_year_id, fsa_crop_id,
{mc.market_crop_type_id}, {mc.price_factor})
returning id;

"""

            for ct in mc.contracts.all():
                sql += f"""
INSERT INTO public.main_contract(
contract_date, bushels, terminal,
contract_number, delivery_start_date,
delivery_end_date, market_crop_id,
basis_price, futures_price)
VALUES (
{dstr(ct.contract_date)}, {ct.bushels}, {qt(ct.terminal)},
{qt(ct.contract_number)}, {dstr(ct.delivery_start_date)},
{dstr(ct.delivery_end_date)}, market_crop_id,
{nz(ct.basis_price)}, {nz(ct.futures_price)});

"""

            for fc in mc.farm_crops.all():
                sql += f"""
INSERT INTO public.main_farmcrop(
planted_acres, ta_aph_yield, adj_yield, rate_yield,
ye_use, ta_use, subcounty, coverage_type,
product_type, base_coverage_level, sco_use,
eco_level, prot_factor, ins_practice, ins_practices,
farm_crop_type_id, farm_year_id, ins_crop_type_id,
market_crop_id, cty_yield_final, harv_price_disc_end,
proj_price_disc_end)
VALUES (
{fc.planted_acres}, {fc.ta_aph_yield}, {fc.adj_yield}, {fc.rate_yield},
{bstr(fc.ye_use)}, {bstr(fc.ta_use)}, {qt(fc.subcounty)}, {nz(fc.coverage_type)},
{nz(fc.product_type)}, {nz(fc.base_coverage_level)}, {bstr(fc.sco_use)},
{nz(fc.eco_level)}, {fc.prot_factor}, {fc.ins_practice},
{astr(fc.ins_practices)}, {fc.farm_crop_type_id},
farm_year_id, {fc.ins_crop_type_id},
market_crop_id, {dstr(fc.cty_yield_final)},
{dstr(fc.harv_price_disc_end)},
{dstr(fc.proj_price_disc_end)})
returning id;

"""
                if fc.has_budget():
                    bc = fc.farmbudgetcrop
                    sql += f"""
INSERT INTO public.main_farmbudgetcrop(
farm_yield, county_yield, yield_variability, other_gov_pmts,
other_revenue, fertilizers, pesticides, seed, drying,
storage, other_direct_costs, machine_hire_lease, utilities,
machine_repair, fuel_and_oil, light_vehicle, machine_depr,
labor_and_mgmt, building_repair_and_rent, building_depr,
insurance, misc_overhead_costs, interest_nonland,
other_overhead_costs, rented_land_costs, budget_id,
description, state_id, farm_crop_type_id, is_irr,
is_rot, farm_crop_id, farm_year_id,
budget_crop_id, budget_date,
baseline_yield_for_var_rent, is_farm_yield_final,
yield_factor, are_costs_final)
VALUES (
{bc.farm_yield}, {bc.county_yield}, {bc.yield_variability}, {bc.other_gov_pmts},
{bc.other_revenue}, {bc.fertilizers}, {bc.pesticides}, {bc.seed}, {bc.drying},
{bc.storage}, {bc.other_direct_costs}, {bc.machine_hire_lease}, {bc.utilities},
{bc.machine_repair}, {bc.fuel_and_oil}, {bc.light_vehicle}, {bc.machine_depr},
{bc.labor_and_mgmt}, {bc.building_repair_and_rent}, {bc.building_depr},
{bc.insurance}, {bc.misc_overhead_costs}, {bc.interest_nonland},
{bc.other_overhead_costs}, {bc.rented_land_costs}, {nz(bc.budget_id)},
{qt(bc.description)}, {bc.state_id}, {bc.farm_crop_type_id},
{bstr(bc.is_irr)},
{bstr(bc.is_rot)}, farm_crop_id, farm_year_id,
{nz(bc.budget_crop_id)}, {dstr(bc.budget_date)},
{bc.baseline_yield_for_var_rent}, {bstr(bc.is_farm_yield_final)},
{bc.yield_factor}, {bstr(bc.are_costs_final)});

"""

    return sql
