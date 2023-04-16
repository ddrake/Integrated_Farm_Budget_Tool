-- After migration 0002
-- Delete about 19 million orphaned records, leaving about 400,000.
delete from ext_areacoveragelevel 
where insurance_offer_id not in (select id from ext_insuranceoffer);

-- Delete newly orphaned records.  Never completed after 7+ hours.
-- Maybe shouldn't have indexed core_arearate.area_rate_id...
delete from ext_arearate 
where area_rate_id not in (select area_rate_id from ext_areacoveragelevel);
