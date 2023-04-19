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

-- after migration 0016
INSERT INTO public.ext_optionrate1(
	state_id, county_code, commodity_id, commodity_type_id, practice, option_rate)
select state_id, county_code, commodity_id, commodity_type_id, practice, array_agg(option_rate)
from
	(SELECT id, state_id, county_code, commodity_id, commodity_type_id, practice, insurance_option_id,
	option_rate FROM public.ext_optionrate
	order by state_id, county_code, commodity_id, commodity_type_id, practice, insurance_option_id) q
group by state_id, county_code, commodity_id, commodity_type_id, practice;


-- after migration 0020
INSERT INTO public.ext_arearate1(
	insurance_offer_id, price_volatility_factor, base_rate)
SELECT insurance_offer_id, vol_factor, array_agg(base_rate)
FROM
	(SELECT insurance_offer_id, ROUND(100*price_volatility_factor) vol_factor, coverage_level, base_rate
		FROM public.ext_areacoveragelevel acl inner join public.ext_arearate ar on acl.area_rate_id = ar.area_rate_id
		order by insurance_offer_id, price_volatility_factor, coverage_level) q
GROUP BY insurance_offer_id, vol_factor;


-- after migration 0023
INSERT INTO public.ext_arearate2(
	state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor, base_rate)
SELECT state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor, array_agg(brate) as base_rate
FROM
	(SELECT state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor, insurance_plan_id,
	 base_rate || array_fill(NULL::real, array[8 - array_length(base_rate, 1)]) brate
	  FROM public.ext_insuranceofferarea ioa inner join public.ext_arearate1 ar1
	  on ioa.id = ar1.insurance_offer_id
	Order by state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor, insurance_plan_id) q
GROUP BY state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor;


-- after migration 0024
-- I decided it's better not to bundle up rates for all insurance plans, because
-- data is missing for some combinations of insurance plan, county, crop.  So
-- the business logic would have to do extra work to unpack, count non-None values, etc.
-- The table arearate2 has 1,923,769 records, which is not that bad.
INSERT INTO public.ext_arearate2(
	state_id, county_code, commodity_id, commodity_type_id, practice,
	price_volatility_factor, insurance_plan_id, base_rate)
SELECT state_id, county_code, commodity_id, commodity_type_id, practice,
  price_volatility_factor, insurance_plan_id, base_rate
    FROM public.ext_insuranceofferarea ioa inner join public.ext_arearate1 ar1
    on ioa.id = ar1.insurance_offer_id
Order by state_id, county_code, commodity_id, commodity_type_id, practice,
  price_volatility_factor, insurance_plan_id;
	
-- Delete practices from arearate2 to remove duplicates
-- See cpractices in premium.py
delete from ext_arearate2 where practice not in(3, 53)

-- Remove the first base rate (65% not used) for AYP 
UPDATE public.ext_arearate2
SET base_rate = base_rate[2:6]
	WHERE insurance_plan_id=4;


-- after migration 0025 (add price)
DELETE FROM public.ext_price where expected_yield is NULL;
DELETE FROM public.ext_price where insurance_plan_id <> 4;
DELETE FROM public.ext_price where practice not in (3, 53);

-- after migration 0028
-- No rates for 'URA'
DELETE FROM public.ext_subcountyrate where subcounty_id = 'URA';
-- Remove duplicates
DELETE FROM public.ext_subcountyrate where practice not in (3, 53);

-- After migration 0032 (make beta, unit_discount foreign keys)
UPDATE public.ext_insuranceofferent
	SET beta_id = beta1_id, unit_discount_id=unit1_discount_id;

-- After migration 0034
-- This sets high_risk=true for all.
UPDATE public.ext_subcountyrate
	SET high_risk=true where subcounty_id is not null and subcounty_id <> 'URA';

-- Working on stored view for all enterprise data.  Getting multiple rows.  Thoughts:
-- Maybe make the 'main table' insuranceofferent cross joined to subsidy
-- full joined to subcountyrate with high risk and subcounty_id in the select set.
-- 
-- Then left join to all the other tables
SELECT ioe.id, ioe.state_id, ioe.county_code, scr.subcounty_id, ioe.commodity_id, ioe.commodity_type_id, ioe.practice,
ud.enterprise_discount_factor, b.draw, scr.rate_method_id, scr.subcounty_rate, sub.subsidy,
br.refyield, br.refrate, br.exponent, br.fixedrate, rd.rate_differential_factor, ef.enterprise_residual_factor_r,
ef.enterprise_residual_factor_y, opr.option_rate
	FROM public.ext_insuranceofferent ioe
LEFT JOIN public.ext_beta b on ioe.beta_id=b.id
LEFT JOIN public.ext_unitdiscount ud on ioe.unit_discount_id=ud.id
LEFT JOIN public.ext_subcountyrate scr on ioe.state_id=scr.state_id
	and ioe.county_code=scr.county_code and ioe.commodity_id=scr.commodity_id
	and ioe.commodity_type_id=scr.commodity_type_id
CROSS JOIN public.ext_subsidy sub
LEFT JOIN public.ext_baserate br on ioe.state_id=br.state_id and ioe.county_code=br.county_code
    and ioe.commodity_id=br.commodity_id and ioe.commodity_type_id=br.commodity_type_id 
	and ioe.practice=br.practice
LEFT JOIN public.ext_ratedifferential rd on ioe.state_id = rd.state_id and ioe.county_code=rd.county_code
  	and ioe.commodity_id=rd.commodity_id and ioe.commodity_type_id=rd.commodity_type_id
	and ioe.practice = rd.practice
LEFT JOIN public.ext_enterprisefactor ef on ioe.state_id = ef.state_id and ioe.county_code=ef.county_code
	and ioe.commodity_id=ef.commodity_id and ioe.commodity_type_id=ef.commodity_type_id and ioe.practice=ef.practice
LEFT JOIN public.ext_optionrate opr on ioe.state_id=opr.state_id and ioe.county_code=opr.county_code
	and ioe.commodity_id=opr.commodity_id and ioe.commodity_type_id=opr.commodity_type_id and ioe.practice=opr.practice
where ioe.state_id=1 and ioe.county_code=19;

