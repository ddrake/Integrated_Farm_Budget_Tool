-- After migration 0002
-- Delete about 19 million orphaned records, leaving about 400,000.
delete from ext_areacoveragelevel 
where insurance_offer_id not in (select id from ext_insuranceoffer);

-- After migration 0003
-- Delete newly orphaned records.  Never completed after 7+ hours.
-- Completed in a few seconds after adding index to insuranceoffer.area_rate_id
-- leaving 5 million records.
delete from ext_arearate 
where area_rate_id not in (select area_rate_id from ext_areacoveragelevel);

-- After migration 0004
-- Split insuranceoffer into two tables, one for area and a new one for ent
INSERT INTO public.ext_insuranceofferent(
	id, county_code, beta_id, unit_discount_id, practice,
	commodity_id, commodity_type_id, insurance_plan_id, state_id)
	select id, county_code, beta_id, unit_discount_id, practice,
	commodity_id, commodity_type_id, insurance_plan_id, state_id
	from public.ext_insuranceoffer where insurance_plan_id = 1

DELETE FROM public.ext_insuranceoffer where insurance_plan_id in(1, 2, 3);

-- Split coverageleveldifferential into two tables, 
-- one for ratedifferential and a new one for enterprisefactor
-- enterprise factor has two sets of enterprise_residual_factors,
-- one for YP and the other for RP/RP-HPE
INSERT INTO public.ext_enterprisefactor(
	county_code, coverage_level, enterprise_residual_factor,
	enterprise_residual_factor_prior, practice,
	commodity_id, commodity_type_id, coverage_type_id, insurance_plan_id,
	state_id, subcounty_id)
SELECT county_code, coverage_level, enterprise_residual_factor,
    enterprise_residual_factor_prior, practice,
	commodity_id, commodity_type_id, coverage_type_id, insurance_plan_id,
	state_id, subcounty_id
	FROM public.ext_coverageleveldifferential where insurance_plan_id in(1, 2);

-- Only one set of rate_differental_factors
DELETE
FROM public.ext_coverageleveldifferential where insurance_plan_id <> 1;
	
-- Ensure no orphans
DELETE
FROM public.ext_beta where beta_id not in
(select beta_id from public.ext_insuranceofferent);

-- Ensure no orphans
DELETE FROM public.ext_unitdiscount
where unit_discount_id not in
(SELECT unit_discount_id FROM public.ext_insuranceofferent);

-- Remove duplicates
DELETE FROM public.ext_subcountyrate
where insurance_plan_id <> 1;

-- Remove duplicates
DELETE FROM public.ext_optionrate
where insurance_plan_id <> 1;

-- After migration 0007
INSERT INTO public.ext_unitdiscount1(id, enterprise_discount_factor)
SELECT unit_discount_id, array_agg(enterprise_discount_factor)
FROM 
(select unit_discount_id, coverage_level,
 area_low_qty, enterprise_discount_factor
 from public.ext_unitdiscount
 order by unit_discount_id, coverage_level, area_low_qty) q
GROUP BY unit_discount_id;

-- After migration 0008
INSERT INTO public.ext_beta1 (id, draw)
select beta_id, array_agg(draw) from
(
	select beta_id, rownum, col, draw from
		(SELECT beta_id, row_number() over (order by beta_id) rownum,
		 0 col, yield_draw draw FROM public.ext_beta
		 union select beta_id, row_number() over (order by beta_id)  rownum,
		 1 col, price_draw draw FROM public.ext_beta) q
	order by beta_id, rownum, col
) qq group by beta_id;


-- We assume that Enterprise Unit subsidy will only ever depend on coverage level
DELETE
	FROM public.ext_subsidy
	where insurance_plan_id <> 1 or unit_structure_code <> 'EU'
	or commodity_id is not null;

-- After migration 0009
INSERT INTO public.ext_subsidy1(id, subsidy)
SELECT 1, array_agg(subsidy) from
(select coverage_level, subsidy
 FROM public.ext_subsidy
 order by coverage_level) q;

-- After migration 0010
-- I had to reimport BaseRate because it didn't include two critical columns
-- Assume BaseRate will never depend on insurance_plan_id
DELETE	FROM public.ext_baserate
where insurance_plan_id <> 1;

-- After migration 0011
INSERT INTO public.ext_baserate1(
	state_id, county_code, commodity_id, commodity_type_id, practice, 
	refyield, refrate, exponent, fixedrate)
SELECT state_id, county_code, commodity_id, commodity_type_id, practice,
array_agg(refyld), array_agg(refrat), array_agg(expo), array_agg(frat) from
	(SELECT id, col, state_id, county_code, commodity_id, commodity_type_id, practice,
	refyld, refrat, expo, frat from
	   (SELECT id, 0 col,
		reference_yield refyld, reference_rate refrat,
		exponent expo, fixed_rate frat,
		state_id, county_code, commodity_id, commodity_type_id, practice
		FROM public.ext_baserate
		UNION SELECT id, 1 col,
		reference_yield_prior refyld, reference_rate_prior refrat,
		exponent_prior expo, fixed_rate_prior frat,
		state_id, county_code, commodity_id, commodity_type_id, practice
		FROM public.ext_baserate) q
	ORDER BY id, col) qq
GROUP BY id, state_id, county_code, commodity_id, commodity_type_id, practice;

-- Delete duplicates (no particular reason for the choice of commodity and state)
DELETE FROM public.ext_comborevenuefactor
where commodity_id <> 41 or state_id <> 17;

-- After migration 0012
INSERT INTO public.ext_comborevenuefactor1(id, std_deviation_qty, mean_qty)
SELECT round(10000*base_rate), std_deviation_qty, mean_qty
	FROM public.ext_comborevenuefactor
	order by base_rate;

-- Delete Catastrophic Rates
DELETE
FROM public.ext_ratedifferential
WHERE coverage_type_id = 'C';

-- After migration 0014
INSERT INTO public.ext_ratedifferential1(
	state_id, county_code, high_risk, commodity_id, commodity_type_id, practice,
	rate_differential_factor)
SELECT state_id, county_code, high_risk, commodity_id, commodity_type_id, practice, 
array_agg(rate_differential_factor)
FROM
	(SELECT state_id, county_code, high_risk, commodity_id, commodity_type_id,
		practice, coverage_level,
		 rate_differential_factor, col
	FROM
		(SELECT id, state_id, county_code, case when subcounty_id is NULL then true
		   else false end high_risk,
		commodity_id, commodity_type_id, practice, coverage_level,
		 rate_differential_factor, 0 col
		FROM public.ext_ratedifferential
		UNION
		SELECT id, state_id, county_code, case when subcounty_id is NULL then true
	    else false end high_risk,
		commodity_id, commodity_type_id, practice, coverage_level,
		 rate_differential_factor_prior rate_differential_factor, 1 col
		FROM public.ext_ratedifferential) q
	order by 
	state_id, county_code, high_risk, commodity_id, commodity_type_id,
	practice, coverage_level, col) qq
GROUP BY state_id, county_code, high_risk, commodity_id, commodity_type_id, practice;

-- Delete Catastrophic Rates
DELETE FROM public.ext_enterprisefactor
	WHERE coverage_type_id = 'C';

-- after migration 0015
INSERT INTO public.ext_enterprisefactor1(
	state_id, county_code, commodity_id, commodity_type_id, practice, high_risk, 
	enterprise_residual_factor_y, enterprise_residual_factor_r
)
SELECT state_id, county_code, commodity_id, commodity_type_id, practice, high_risk,
array_agg(ent_res_y) enterprise_residual_factor_y,
array_agg(ent_res_r) enterprise_residual_factor_r
FROM
	(SELECT state_id, county_code, commodity_id, commodity_type_id, practice, coverage_level,
	high_risk, col, sum(enterprise_residual_factor_y) as ent_res_y,
	sum(enterprise_residual_factor_r) as ent_res_r
	FROM
		(SELECT state_id, county_code, commodity_id, commodity_type_id, practice, coverage_level,
		case when subcounty_id is NULL then true
		else false end high_risk, 0 col,insurance_plan_id,
		case when insurance_plan_id = 1 then enterprise_residual_factor
		else 0 end as enterprise_residual_factor_y,
		case when insurance_plan_id = 2 then enterprise_residual_factor
		else 0 end as enterprise_residual_factor_r
		FROM public.ext_enterprisefactor
		UNION
		SELECT state_id, county_code, commodity_id, commodity_type_id, practice, coverage_level,
		case when subcounty_id is NULL then true else
			false end high_risk, 1 col,insurance_plan_id,
		case when insurance_plan_id = 1 then enterprise_residual_factor_prior
		else 0 end as enterprise_residual_factor_y,
		case when insurance_plan_id = 2 then enterprise_residual_factor_prior
		else 0 end as enterprise_residual_factor_r
		FROM public.ext_enterprisefactor
		order by state_id, county_code, commodity_id, commodity_type_id, practice,
		coverage_level, high_risk, col, insurance_plan_id) q
	GROUP BY state_id, county_code, commodity_id, commodity_type_id, practice, coverage_level,
	high_risk, col) qq
GROUP BY state_id, county_code, commodity_id, commodity_type_id, practice, high_risk;
