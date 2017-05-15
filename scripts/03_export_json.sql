/* requêtes SQL de génération des fichiers JSON destinés à l'init de la BAN */


/* municipality depuis COG */
copy (select format('{"type":"municipality","source":"INSEE/COG (2015)","insee":"%s","name":"%s"}',insee,replace(trim(replace(replace(coalesce(artmin,''),'(',''),')','')||' '||nccenr), E'\' '::text, E'\''::text)) from insee_cog_2015 order by insee) to '/tmp/01_municipalities_cog-insee.json';


/* groups depuis FANTOIR */
copy (select format('{"type":"group","source":"DGFIP/FANTOIR (2015-07)","group":"%s","municipality:insee":"%s","fantoir":"%s","name":"%s" %s}',case when type_voie='1' then 'way' else 'area' end,code_insee,left(replace(fantoir,'_',''),9),trim(replace(format('%s %s',nature_voie,libelle_voie),'"',' ')), case when date_annul='0000000' then '' else format(',"attributes": {"fantoir:date_annul":"%s"}',date_annul) end) from dgfip_fantoir f join insee_cog_2015 c on (insee=code_insee) order by fantoir) to '/tmp/02_groups-fantoir_dgfip.json';

copy (select format('{"type":"group","source":"DGFIP/FANTOIR (2015-07)","group":"%s","municipality:insee":"%s","fantoir":"%s","name":"%s" %s}',case when type_voie='1' then 'way' else 'area' end,code_insee,left(replace(fantoir,'_',''),9),trim(replace(format('%s %s',nature_voie,libelle_voie),'"',' ')), case when date_annul='0000000' then '' else format(',"attributes": {"fantoir:date_annul":"%s"}',date_annul) end) from dgfip_fantoir f join insee_cog_2015 c on (insee=code_insee) where insee like '33%' or insee like '06%' order by fantoir) to '/tmp/02_0633-groups-fantoir_dgfip.json';


/* postcode depuis données RAN */
copy (select format('{"type":"postcode","source":"La Poste (2016-03)","postcode":"%s","name":"%s","municipality:insee":"%s"}',co_postal,lb_l6,co_insee) from ran_postcode order by co_insee) to '/tmp/03a_postcodes-laposte-ran.json';
copy (select format('{"type":"postcode","source":"La Poste (2015)","postcode":"%s","name":"%s","municipality:insee":"%s"}',cp,libelle,insee) from poste_cp left join ran_postcode ra on (ra.co_insee=insee and co_postal=cp) where co_postal is null order by insee) to '/tmp/03b_postcodes-laposte-od2015.json';


/* housenumber depuis DGFiP/BANO */
copy (select format('{"type":"housenumber", "source":"DGFiP/BANO (2016-04)", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s"}', left(h.fantoir,5)||left(right(h.fantoir,5),4),left(upper(numero)||' ',strpos(upper(numero)||' ',' ')-1),trim(right(upper(numero)||' ',-strpos(upper(numero)||' ',' ')))) from dgfip_housenumbers h JOIN dgfip_fantoir f ON (f.fantoir10=h.fantoir AND trim(h.voie_fantoir)=trim(nature_voie||' '||libelle_voie)) GROUP BY h.fantoir, upper(numero)) to '/tmp/04_housenumbers_dgfip.json' ;

copy (select format('{"type":"housenumber", "source":"DGFiP/BANO (2016-04)", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s"}', left(h.fantoir,5)||left(right(h.fantoir,5),4),left(upper(numero)||' ',strpos(upper(numero)||' ',' ')-1),trim(right(upper(numero)||' ',-strpos(upper(numero)||' ',' ')))) from dgfip_housenumbers h JOIN dgfip_fantoir f ON (f.fantoir10=h.fantoir AND trim(h.voie_fantoir)=trim(nature_voie||' '||libelle_voie)) WHERE h.fantoir LIKE '06%' or h.fantoir LIKE '33%' GROUP BY h.fantoir, upper(numero)) to '/tmp/04_0633-housenumbers_dgfip.json' ;


/* position depuis DGFiP/BANO */
copy (select format('{"type":"position", "kind":"entrance", "source":"DGFiP/BANO (2016-04)", "housenumber:cia": "%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',left(h.fantoir,5),left(right(h.fantoir,5),4),left(upper(numero)||' ',strpos(upper(numero)||' ',' ')-1),trim(right(upper(numero)||' ',-strpos(upper(numero)||' ',' '))))), round(lon::numeric,7)::text, round(lat::numeric,7)::text) from dgfip_housenumbers h JOIN dgfip_fantoir f ON (f.fantoir10=h.fantoir AND trim(h.voie_fantoir)=trim(nature_voie||' '||libelle_voie))) to '/tmp/05_positions_dgfip.json';

copy (select format('{"type":"position", "kind":"entrance", "source":"DGFiP/BANO (2016-04)", "housenumber:cia": "%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',left(h.fantoir,5),left(right(h.fantoir,5),4),left(upper(numero)||' ',strpos(upper(numero)||' ',' ')-1),trim(right(upper(numero)||' ',-strpos(upper(numero)||' ',' '))))), round(lon::numeric,7)::text, round(lat::numeric,7)::text) from dgfip_housenumbers h JOIN dgfip_fantoir f ON (f.fantoir10=h.fantoir AND trim(h.voie_fantoir)=trim(nature_voie||' '||libelle_voie)) WHERE h.fantoir LIKE '06%' or h.fantoir LIKE '33%') to '/tmp/05_0633-positions_dgfip.json';


/* export housenumbers BAN qui ont un fant_voie et pas de fant_ld */
\copy (select format('{"type":"housenumber", "source":"BAN (2016-06-05)", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s", "ign":"%s", "postcode:code":"%s"}', upper(format('%s_%s_%s_%s',code_insee,fant_voie,numero, coalesce(rep,''))), code_insee||fant_voie, numero, coalesce(rep,''), min(id), code_post) from banodbl where fant_voie is not null and fant_ld is null group by code_insee, code_post, fant_voie, fant_ld, numero, rep) to 06a_housenumbers_ban.json ;

\copy (select format('{"type":"housenumber", "source":"BAN (2016-06-05)", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s", "ign":"%s", "postcode:code":"%s"}', upper(format('%s_%s_%s_%s',code_insee,fant_voie,numero, coalesce(rep,''))), code_insee||fant_voie, numero, coalesce(rep,''), min(id), code_post) from banodbl where (code_insee like '06%' or code_insee like '33%') and fant_voie is not null and fant_ld is null group by code_insee, code_post, fant_voie, fant_ld, numero, rep) to 06a_0633-housenumbers_ban.json ;


/* export housenumbers BAN qui ont un fant_ld et pas de fant_voie */
\copy (select format('{"type":"housenumber", "source":"BAN (2016-06-05)", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s", "ign":"%s", "postcode:code":"%s"}', upper(format('%s_%s_%s_%s',code_insee,fant_ld,numero, coalesce(rep,''))), code_insee||fant_ld, numero, coalesce(rep,''), min(id), code_post) from banodbl where fant_voie is null and fant_ld is not null group by code_insee, code_post, fant_voie, fant_ld, numero, rep) to 06b_housenumbers_ban.json ;

\copy (select format('{"type":"housenumber", "source":"BAN (2016-06-05)", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s", "ign":"%s", "postcode:code":"%s"}', upper(format('%s_%s_%s_%s',code_insee,fant_ld,numero, coalesce(rep,''))), code_insee||fant_ld, numero, coalesce(rep,''), min(id), code_post) from banodbl where fant_voie is null and fant_ld is not null and (code_insee like '06%' or code_insee like '33%') group by code_insee, code_post, fant_voie, fant_ld, numero, rep) to 06b_0633-housenumbers_ban.json ;


/* export positions BAN qui ont un fant_voie et pas de fant_ld */
\copy (select format('{"type":"position", "kind":"unknown", "source":"BAN (2016-06-05)", "housenumber:cia": "%s", "ign":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',code_insee,fant_voie,numero, coalesce(rep,''))), id, lon::text, lat::text) from banodbl where fant_voie is not null and fant_ld is null) to 07a_positions_ban.json;

\copy (select format('{"type":"position", "kind":"unknown", "source":"BAN (2016-06-05)", "housenumber:cia": "%s", "ign":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',code_insee,fant_voie,numero, coalesce(rep,''))), id, lon::text, lat::text) from banodbl where (code_insee like '06%' or code_insee like '33%') and fant_voie is not null and fant_ld is null) to 07a_0633-positions_ban.json;


/* export positions BAN qui ont un fant_ld et pas de fant_voie */
\copy (select format('{"type":"position", "kind":"unknown", "source":"BAN (2016-06-05)", "housenumber:cia": "%s", "ign":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',code_insee,fant_ld,numero, coalesce(rep,''))), id, lon::text, lat::text) from banodbl where fant_voie is null and fant_ld is not null) to 07b_positions_ban.json;

\copy (select format('{"type":"position", "kind":"unknown", "source":"BAN (2016-06-05)", "housenumber:cia": "%s", "ign":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', upper(format('%s_%s_%s_%s',code_insee,fant_ld,numero, coalesce(rep,''))), id, lon::text, lat::text) from banodbl where fant_voie is null and fant_ld is not null and (code_insee like '06%' or code_insee like '33%')) to 07b_0633-positions_ban.json;



/******* que fait-on de ceux avec fant_voie ET fant_ld ? ********/



/* groups IGN rapprochés de FANTOIR */
copy (
select format('{"type":"group", "source":"IGN (2016-06)", "fantoir":"%s", "ign": "%s" %s %s}',left(id_fantoir,9), id_pseudo_fpb, case when type_d_adressage='Classique' then ',"addressing":"classical"' when type_d_adressage='Mixte' then ',"addressing":"mixed"' when type_d_adressage='Linéaire' then ',"addressing":"linear"' when type_d_adressage='Anarchique' then ',"addressing":"anarchical"' when type_d_adressage='Métrique' then ',"addressing":"metric"' else '' end, case when alias is not null then ',"alias":"'||alias||'"' else '' end )
from ign_group i
where id_fantoir is not null
order by id_pseudo_fpb
) to '/tmp/08a_groups-sga-ign-rapproches.json';

copy (
select format('{"type":"group", "source":"IGN (2016-06)", "fantoir":"%s", "ign": "%s" %s %s}',
  left(id_fantoir,9),
  id_pseudo_fpb,
  case when type_d_adressage='Classique' then ',"addressing":"classical"' when type_d_adressage='Mixte' then ',"addressing":"mixed"' when type_d_adressage='Linéaire' then ',"addressing":"linear"' when type_d_adressage='Anarchique' then ',"addressing":"anarchical"' when type_d_adressage='Métrique' then ',"addressing":"metric"' else '' end,
  case when alias is not null then ',"alias":"'||alias||'"' else '' end )
from ign_group i
where id_fantoir like '06%' or id_fantoir like '33%'
order by id_pseudo_fpb
) to '/tmp/08a_0633-groups-sga-ign-rapproches.json';

/* groups IGN non rapprochés de FANTOIR (création potentielle de doublons) */
copy (
select format('{"type":"group", "group": "%s", "source":"IGN (2016-06)", "ign": "%s", "name": "%s", "municipality:insee": "%s" %s %s}',
  case when nom_afnor ~ '^(LIEU DIT |LD )' then 'area' else 'way' end,
  id_pseudo_fpb,
  nom,
  code_insee,
  case when type_d_adressage='Classique' then ',"addressing":"classical"' when type_d_adressage='Mixte' then ',"addressing":"mixed"' when type_d_adressage='Linéaire' then ',"addressing":"linear"' when type_d_adressage='Anarchique' then ',"addressing":"anarchical"' when type_d_adressage='Métrique' then ',"addressing":"metric"' else '' end,
  case when alias is not null then ',"alias":"'||alias||'"' else '' end )
from ign_group i
where id_fantoir is null
order by id_pseudo_fpb
) to '/tmp/08b_groups-sga-ign-non-rapproches.json';

copy (
select format('{"type":"group", "group": "%s", "source":"IGN (2016-06)", "ign": "%s", "name": "%s", "municipality:insee": "%s" %s %s}',
  case when nom_afnor ~ '^(LIEU DIT |LD )' then 'area' else 'way' end,
  id_pseudo_fpb,
  nom,
  code_insee,
  case when type_d_adressage='Classique' then ',"addressing":"classical"' when type_d_adressage='Mixte' then ',"addressing":"mixed"' when type_d_adressage='Linéaire' then ',"addressing":"linear"' when type_d_adressage='Anarchique' then ',"addressing":"anarchical"' when type_d_adressage='Métrique' then ',"addressing":"metric"' else '' end,
  case when alias is not null then ',"alias":"'||alias||'"' else '' end )
from ign_group i
where id_fantoir is null and (code_insee like '06%' or code_insee like '33%')
order by id_pseudo_fpb
) to '/tmp/08b_0633-groups-sga-ign-non-rapproches.json';


/* housenumbers IGN absents du cadastre (group rapprochés) */
copy (
select format('{"type":"housenumber", "source":"IGN (2016-06)", "ign":"%s", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s"}', min(id), upper(format('%s_%s_%s_%s',left(g.id_fantoir,5),right(g.id_fantoir,4),i.numero, coalesce(i.rep,''))), g.id_fantoir, i.numero, i.rep)
from ign_housenumber i
join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
join dgfip_fantoir f on (g.id_fantoir=f.fantoir2)
left join dgfip_housenumbers d on (d.fantoir=f.fantoir10 and d.numero=trim(i.numero||' '||coalesce(i.rep,'')))
where d.numero is null
group by g.id_fantoir, i.numero, i.rep
) to '/tmp/08c_housenumbers_sga-ign_missing.json' ;

copy (
select format('{"type":"housenumber", "source":"IGN (2016-06)", "ign":"%s", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s"}', min(id), upper(format('%s_%s_%s_%s',left(g.id_fantoir,5),right(g.id_fantoir,4),i.numero, coalesce(i.rep,''))), g.id_fantoir, i.numero, i.rep)
from ign_housenumber i
join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
join dgfip_fantoir f on (g.id_fantoir=f.fantoir2)
left join dgfip_housenumbers d on (d.fantoir=f.fantoir10 and d.numero=trim(i.numero||' '||coalesce(i.rep,'')))
where d.numero is null and (g.code_insee like '06%' or g.code_insee like '33%')
group by g.id_fantoir, i.numero, i.rep
) to '/tmp/08c_0633-housenumbers_sga-ign_missing.json' ;

/* housenumbers IGN absents du cadastre (group non rapprochés) */
\copy (select format('{"type":"housenumber", "source":"IGN (2016-06)", "ign":"%s", "cia":"%s", "group:ign":"%s", "numero":"%s", "ordinal":"%s"}', min(id), upper(format('%s_%s_%s_%s',left(i.id_fantoir,5),right(i.id_fantoir,4),i.numero, coalesce(i.rep,''))), g.id_pseudo_fpb, i.numero, i.rep)
from ign_housenumber i
join dgfip_fantoir f on (i.id_fantoir=f.fantoir2)
left join dgfip_housenumbers d on (d.fantoir=f.fantoir10 and d.numero=trim(i.numero||' '||coalesce(i.rep,'')))
where d.numero is null
group by i.id_fantoir, i.numero, i.rep)
to 08d_housenumbers_sga-ign_missing.json ;

copy (
select format('{"type":"housenumber", "source":"IGN (2016-06)", "ign":"%s", "cia":"%s", "group:fantoir":"%s", "numero":"%s", "ordinal":"%s"}', min(id), upper(format('%s_%s_%s_%s',left(g.id_fantoir,5),right(g.id_fantoir,4),i.numero, coalesce(i.rep,''))), g.id_fantoir, i.numero, i.rep)
from ign_housenumber i
join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
where g.id_fantoir is not null and (g.id_pseudo_fpb like '06%' or g.id_pseudo_fpb like '33%')
group by g.id_fantoir, g.id_pseudo_fpb, i.numero, i.rep
) to '/tmp/08d_0633-housenumbers_sga-ign_missing.json' ;

copy (
select format('{"type":"housenumber", "source":"IGN (2016-06)", "ign":"%s", "group:ign":"%s", "numero":"%s", "ordinal":"%s"}', min(id), g.id_pseudo_fpb, i.numero, i.rep)
from ign_housenumber i
join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
where g.id_fantoir is null and (g.id_pseudo_fpb like '06%' or g.id_pseudo_fpb like '33%')
group by g.id_pseudo_fpb, i.numero, i.rep
) to '/tmp/08e_0633-housenumbers_sga-ign_missing.json' ;


/* position: rapprochements IGN/DGFiP */
\copy (select format('{"type":"position", %s "source":"IGN (2016-06)", "housenumber:cia": "%s", "ign": "%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', kind_pos, upper(format('%s_%s_%s_%s',left(f.fantoir,5),left(right(f.fantoir,5),4),i.numero,coalesce(i.rep,''))), i.id, i.lon::text, i.lat::text) from ign_housenumber i join dgfip_fantoir f on (i.id_pseudo_fpb=f.fantoir2) left join dgfip_housenumbers d on (d.fantoir=f.fantoir10 and d.numero=trim(i.numero||' '||coalesce(i.rep,''))) where d.numero is not null) to 09a_old_positions_sga-ign.json ;

copy (
select format('{"type":"position", %s "source":"IGN/2 (2016-06)", "housenumber:cia": "%s", "ign": "%s", %s "geometry": {"type":"Point","coordinates":[%s,%s]}}', kind_pos, upper(format('%s_%s_%s_%s',left(g.id_fantoir,5),right(g.id_fantoir,4),i.numero,coalesce(i.rep,''))), i.id, case when designation_de_l_entree !='' then format('"name":"%s",',designation_de_l_entree) else '' end, i.lon::text, i.lat::text) from ign_housenumber i join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
where g.id_fantoir is not null
and (i.code_insee like '06%' or i.code_insee like '33%')
) to '/tmp/09a_0633-positions_sga-ign-rapprochees.json' ;

copy (
select format('{"type":"position", %s "source":"IGN (2016-06)", "housenumber:ign": "%s", "ign": "%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}', i.kind_pos, min(h.id), i.id, i.lon::text, i.lat::text)
from ign_housenumber i
join ign_group g on (g.id_pseudo_fpb=i.id_pseudo_fpb)
join ign_housenumber h on (g.id_pseudo_fpb=h.id_pseudo_fpb and h.numero=i.numero and h.rep=i.rep)
where g.id_fantoir is null
and (i.code_insee like '06%' or i.code_insee like '33%')
group by i.kind_pos,i.id, i.lon, i.lat
) to '/tmp/09b_0633-positions_sga-ign-non-rapprochees.json' ;


/* rapprochements IGN/DGFiP 'à la plaque' avec plus de 10m de différence */
\copy (select i.*, d.lon as lon_dgfip, d.lat as lat_dgfip, st_distance(st_makepoint(i.lon,i.lat)::geography, st_makepoint(d.lon,d.lat)::geography) as dist from ign_housenumber i join dgfip_fantoir f on (i.id_pseudo_fpb=f.fantoir2) left join dgfip_housenumbers d on (d.fantoir=f.fantoir10 and d.numero=trim(i.numero||' '||coalesce(i.rep,''))) where i.type_de_localisation='A la plaque' and d.numero is not null and st_distance(geom, st_makepoint(d.lon,d.lat)::geography)>10 order by st_distance(i.geom, d.geom) desc) to 99_positions_ign_matched_toofar.csv with (format csv, header true);


/* La Poste: mise à jour du matricule dans les group à partir du lien SGA */
copy (
select format('{"type":"group", "source":"IGN/Poste (2016-06)", "ign":"%s", "laposte": "%s"}',i.id_pseudo_fpb, i.id_poste)
from ign_group i
where id_poste is not null
order by i.id_pseudo_fpb
) to '/tmp/10a_groups-poste-matricule_sga.json';

copy (
select format('{"type":"group", "source":"IGN/Poste (2016-06)", "ign":"%s", "laposte": "%s"}',i.id_pseudo_fpb, i.id_poste)
from ign_group i
WHERE id_poste is not null and (i.code_insee like '06%' or i.code_insee like '33%')
order by i.id_pseudo_fpb
) to '/tmp/10a_0633-groups-poste-matricule_sga.json';

/* 10b : group Poste absents du SGA qu'on arrive à rapprocher */
copy (
select format('{"type":"group", "source":"Poste/RAN (2016-06)", "laposte": "%s" %s %s}', right('0000000'||r.co_voie,8), min(',"fantoir":"'||coalesce(f.fantoir2, g.id_fantoir)||'"'), min(',"ign":"'||g.id_pseudo_fpb||'"'))
from ran_group r
left join libelles l1 on (l1.long=r.lb_voie)
left join libelles l2 on (l2.court=l1.court and l1.long!=l2.long)
left join dgfip_fantoir f on (f.code_insee=r.co_insee and l2.long = trim(nature_voie||' '||libelle_voie))
left join ign_group g on (g.code_insee=r.co_insee and (g.nom=l2.long or g.nom_afnor=l2.long))
left join ign_group i on (i.id_poste = right('0000000'||co_voie,8) and i.code_insee=r.co_insee)
WHERE i.id_poste is null
group by r.co_voie
having min(coalesce(f.fantoir2, g.id_fantoir)) is not null or min(g.id_pseudo_fpb) is not null
) to '/tmp/10b_groups-poste_absents_sga.json';

copy (
select format('{"type":"group", "source":"Poste (2016-06)", "laposte": "%s" %s %s}', right('0000000'||r.co_voie,8), min(',"fantoir":"'||coalesce(f.fantoir2, g.id_fantoir)||'"'), min(',"ign":"'||g.id_pseudo_fpb||'"'))
from ran_group r
left join libelles l1 on (l1.long=r.lb_voie)
left join libelles l2 on (l2.court=l1.court and l1.long!=l2.long)
left join dgfip_fantoir f on (f.code_insee=r.co_insee and l2.long = trim(nature_voie||' '||libelle_voie))
left join ign_group g on (g.code_insee=r.co_insee and (g.nom=l2.long or g.nom_afnor=l2.long))
left join ign_group i on (i.id_poste = right('0000000'||co_voie,8) and i.code_insee=r.co_insee)
WHERE i.id_poste is null and (r.co_insee like '06%' or r.co_insee like '33%')
group by r.co_voie
having min(coalesce(f.fantoir2, g.id_fantoir)) is not null or min(g.id_pseudo_fpb) is not null
) to '/tmp/10b_0633-groups-poste_absents_sga.json';

/* 10c : group Poste absents du SGA non rapproché */
copy (
select format('{"type":"group", "source":"Poste/RAN (2016-06)", "municipality:insee":"%s", "name":"%s", "laposte": "%s", "group":"%s"}', r.co_insee, r.lb_voie, right('0000000'||r.co_voie,8), case when lb_voie ~'(LD |LIEU DIT )' then 'area' else 'way' end)
from ran_group r
left join libelles l1 on (long=lb_voie)
left join libelles l2 on (l2.court=l1.court and l1.long!=l2.long)
left join dgfip_fantoir f on (f.code_insee=r.co_insee and l2.long = trim(nature_voie||' '||libelle_voie))
left join ign_group g on (g.code_insee=r.co_insee and (g.nom=l2.long or g.nom_afnor=l2.long))
left join ign_group i on (i.id_poste = right('0000000'||co_voie,8) and i.code_insee=r.co_insee)
WHERE i.id_poste is null
group by r.co_insee,r.co_voie,r.lb_voie
having min(coalesce(f.fantoir2, g.id_fantoir)) is null and min(g.id_pseudo_fpb) is null
order by co_insee,co_voie
) to '/tmp/10c_groups-poste_absents_sga.json';

copy (
select format('{"type":"group", "source":"Poste/RAN (2016-06)", "municipality:insee":"%s", "name":"%s", "laposte": "%s", "group":"%s"}', r.co_insee, r.lb_voie, right('0000000'||r.co_voie,8), case when lb_voie ~'(LD |LIEU DIT )' then 'area' else 'way' end)
from ran_group r
left join libelles l1 on (l1.long=r.lb_voie)
left join libelles l2 on (l2.court=l1.court and l1.long!=l2.long)
left join dgfip_fantoir f on (f.code_insee=r.co_insee and l2.long = trim(nature_voie||' '||libelle_voie))
left join ign_group g on (g.code_insee=r.co_insee and (g.nom=l2.long or g.nom_afnor=l2.long))
left join ign_group i on (i.id_poste = right('0000000'||co_voie,8) and i.code_insee=r.co_insee)
WHERE i.id_poste is null and (r.co_insee like '06%' or r.co_insee like '33%')
group by r.co_insee,r.co_voie,r.lb_voie
having min(coalesce(f.fantoir2, g.id_fantoir)) is null and min(g.id_pseudo_fpb) is null
order by co_insee,co_voie
) to '/tmp/10c_0633-groups-poste_absents_sga.json';


/* 11a La Poste: création du CEA pour le group (via SGA/IGN) */
copy (
select format('{"type":"housenumber", "source":"IGN/Poste (2016-06)", "group:ign":"%s", "laposte": "%s", "numero":null, "postcode:code":"%s"}',left(id_pseudo_fpb,9), co_cea, co_postal)
from ign_group i
join ran_group r on (id_poste=right('0000000'||co_voie,8))
where id_poste is not null
order by id_pseudo_fpb
) to '/tmp/11a_housenumbers_group_cea_poste_sga.json';

copy (
select format('{"type":"housenumber", "source":"IGN/Poste/CP (2016-06)", "group:ign":"%s", "laposte": "%s", "numero":null, "postcode:code":"%s", "municipality:insee":"%s"}',left(id_pseudo_fpb,9), co_cea, co_postal, co_insee)
from ign_group i
join ran_group r on (id_poste=right('0000000'||co_voie,8))
WHERE id_poste is not null and (i.code_insee like '06%' or i.code_insee like '33%')
order by id_pseudo_fpb
) to '/tmp/11a_0633-housenumbers_group_cea_poste_sga.json';

/* 11b La Poste: CEA pour le group absent du SGA/IGN */
copy (
select format('{"type":"housenumber", "source":"Poste/RAN (2016-06)", "numero": null, "group:laposte": "%s", "laposte": "%s"}', right('0000000'||r.co_voie,8), r.co_cea)
from ran_group r
left join ign_group i on (i.id_poste = right('0000000'||co_voie,8) and i.code_insee=r.co_insee)
WHERE i.id_poste is null and (r.co_insee like '06%' or r.co_insee like '33%')
order by co_insee,co_voie
) to '/tmp/11b_0633-cea-groups-poste_absents_sga.json';


/* 12a La Poste: CEA sur housenumbers présents dans SGA/IGN */
copy (
select format('{"type":"housenumber", "source":"IGN/Poste (2016-06)", "ign":"%s","laposte":"%s"}', i.id, h.co_cea)
from ran_housenumber h
join ign_housenumber i on (code_insee=co_insee and id_poste=co_cea)
order by h.co_cea
) to '/tmp/12a_housenumbers_cea.json';

copy (
select format('{"type":"housenumber", "source":"IGN/Poste (2016-06)", "ign":"%s","laposte":"%s"}', i.id, h.co_cea)
from ran_housenumber h
join ign_housenumber i on (code_insee=co_insee and id_poste=co_cea)
where (co_insee like '06%' or co_insee like '33%')
order by h.co_cea
) to '/tmp/12a_0633-housenumbers_cea.json';


/* 12b La Poste: CEA sur housenumbers absents du SGA/IGN */
copy (
select format('{"type":"housenumber", "source":"Poste (2016-06)", "group:laposte":"%s","laposte":"%s","numero":"%s","ordinal":"%s", "postcode:code":"%s"}', right('0000000'||co_voie,8), h.co_cea, va_no_voie, lb_ext, co_postal)
from ran_housenumber h
left join ign_housenumber i on (code_insee=co_insee and id_poste=co_cea)
where id_poste is null and (co_insee like '06%' or co_insee like '33%')
order by h.co_cea
) to '/tmp/12b_0633-housenumbers_cea.json';


/* 12c La Poste: ajout postcode depuis RAN */
copy (
select format('{"type":"housenumber", "source":"Poste/RAN-CP (2016-06)", "laposte":"%s","postcode:code":"%s", "municipality:insee":"%s"}', h.co_cea, h.co_postal, h.co_insee)
from ran_housenumber h
where (co_insee like '06%' or co_insee like '33%')
order by h.co_cea
) to '/tmp/12c_0633-housenumbers_postcode.json';



/* AITF housenumbers */
copy (
select format('{"type":"housenumber", "source":"%s (%s)", "group:fantoir":"%s", "cia":"%s", "numero":"%s", "ordinal":"%s"}',upper(unaccent(source)), maj, upper(replace(left(cia,10),'_','')), format('%s_%s_%s',upper(left(cia,10)),regexp_replace(numero,'^0*',''),upper(coalesce(suffixe,''))), regexp_replace(numero,'^0*',''), upper(coalesce(suffixe,'')))
from aitf_housenumber
where numero !='99999'
) to '/tmp/13_housenumbers_aitf.json';

copy (
select format('{"type":"housenumber", "source":"%s (%s)", "group:fantoir":"%s", "cia":"%s", "numero":"%s", "ordinal":"%s"}',upper(unaccent(source)), maj, upper(replace(left(cia,10),'_','')), format('%s_%s_%s',upper(left(cia,10)),regexp_replace(numero,'^0*',''),upper(coalesce(suffixe,''))), regexp_replace(numero,'^0*',''), upper(coalesce(suffixe,'')))
from aitf_housenumber
where numero !='99999' and (cia like '06%' or cia like '33%')
order by cia
) to '/tmp/13_0633-housenumbers_aitf.json';


/* AITF positions */
copy (
select format('{"type":"position", "kind":"%s", "source":"%s (%s)", "housenumber:cia":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}',case when position='entrée' then 'entrance' when position='bâtiment' then 'building' when position='délivrance postale' then 'postbox' else 'unknown' end, upper(unaccent(source)), maj, format('%s_%s_%s',upper(left(cia,10)),regexp_replace(numero,'^0*',''),upper(coalesce(suffixe,''))), lon, lat)
from aitf_housenumber
where numero !='99999'
) to '/tmp/14_positions_aitf.json';

copy (
select format('{"type":"position", "kind":"%s", "source":"%s (%s)", "housenumber:cia":"%s", "geometry": {"type":"Point","coordinates":[%s,%s]}}',case when position='entrée' then 'entrance' when position='bâtiment' then 'building' when position='délivrance postale' then 'postbox' else 'unknown' end, upper(unaccent(source)), maj, format('%s_%s_%s',upper(left(cia,10)),regexp_replace(numero,'^0*',''),upper(coalesce(suffixe,''))), lon, lat)
from aitf_housenumber
where numero !='99999' and (cia like '06%' or cia like '33%')
) to '/tmp/14_0633-positions_aitf.json';


/* DGFiP noms complets */
copy (
select format('{"type":"group", "source":"DGFiP/BANO (2016-05)", "fantoir":"%s", "name": "%s"}', left(fantoir,9), regexp_replace(nom_cadastre,E'\'[\' ]*',E'\'','g'))
from dgfip_noms_cadastre
where coalesce(fantoir,'')!=''
) to '/tmp/15_group_noms_cadastre_dgfip_bano.json';

copy (
select format('{"type":"group", "source":"DGFiP/BANO (2016-05)", "fantoir":"%s", "name": "%s"}', left(fantoir,9), regexp_replace(nom_cadastre,E'\'[\' ]*',E'\'','g'))
from dgfip_noms_cadastre
where coalesce(fantoir,'')!='' and (fantoir like '06%' or fantoir like '33%')
) to '/tmp/15_0633-group_noms_cadastre_dgfip_bano.json';


/* noms recapitaliés de la BAN par les scripts de sortie ODbL */
\copy (select format('{"type":"group", "source":"BAN (2016-05)", "fantoir":"%s", "name": "%s"}', b.code_insee||b.id_fantoir, b.nom_voie_odbl) from banodbl_group b left join ign_group i on (id_pseudo_fpb=b.code_insee||b.id_fantoir) left join dgfip_fantoir d on (d.fantoir2=b.code_insee||b.id_fantoir ) where coalesce(b.id_fantoir,'')!='' and not (nom_voie_odbl like 'Enceinte%' and nom_afnor like 'EN %')) to 16_group_noms_ban_capitalises.json;






/* rapprochements possible ran_group vers fantoir */
\copy (select rg.co_insee, rg.co_voie, rg.co_cea, rg.lb_voie, max(l2.court) as simplif, max(coalesce(df.nature_voie||' '||df.libelle_voie, ig2.nom)) as match, coalesce(df.fantoir2, ig2.id_fantoir) as fantoir from ran_group rg left join ign_group ig on (ig.code_insee=rg.co_insee and ig.id_poste = right('0000000'||rg.co_voie,8)) left join libelles l1 on (l1.long=rg.lb_voie) left join libelles l2 on (l2.court=l1.court and l2.long!=l1.long) left join dgfip_fantoir df on (df.code_insee=rg.co_insee and l2.long = (df.nature_voie||' '||df.libelle_voie)) left join ign_group ig2 on (ig2.code_insee=rg.co_insee and (ig2.nom = l2.long or ig2.nom_afnor=l2.long)) where ig.id_poste is null and (df.fantoir2 is not null or ig2.id_pseudo_fpb is not null) group by 1,2,3,4,7 order by rg.co_cea) to 99_rapprochements.csv with (format csv, header true);

/* différence entre indices de répétition IGN et POSTE (REP et LB_EXT) */
\copy (select i.id, h.co_cea, i.id_pseudo_fpb, h.va_no_voie, h.lb_ext, i.numero, i.rep from ran_housenumber h join ran_group g on (h.co_voie=g.co_voie) join ign_housenumber i on (i.id_poste=h.co_cea) where lb_ext!=rep order by 3) to 99_rep_mismatch.csv with (format csv, header true);
