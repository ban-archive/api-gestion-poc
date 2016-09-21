
/* préparation king/positionning */
ALTER TABLE ign_housenumber ADD kind_pos text;
UPDATE ign_housenumber SET kind_pos = CASE
  WHEN indice_de_positionnement = '6' THEN '"kind":"unknown",'
  WHEN indice_de_positionnement = '5' THEN '"kind":"area", "positioning":"unknown",'
  WHEN type_de_localisation = 'A la plaque' THEN '"kind":"entrance", '
  WHEN type_de_localisation = 'Projetée du centre parcelle' THEN '"kind":"segment", "positioning":"projection",'
  WHEN type_de_localisation LIKE 'Au complément%' THEN '"kind":"building", '
  WHEN type_de_localisation = 'Interpolée' THEN '"kind":"segment", "positioning":"interpolation",'
  WHEN type_de_localisation LIKE 'A la zone%' THEN '"kind":"area", "positioning":"unknown",'
  ELSE '"kind":"unknown",'
END;

/* préparation geometrie */
ALTER TABLE ign_housenumber ADD geom geography;
UPDATE ign_housenumber SET geom = ST_MakePoint(lon,lat);

/* status de chaque adresse */
ALTER TABLE ign_housenumber ADD status text;

/* groups IGN absents de FANTOIR et cadastre */
ALTER TABLE ign_group ADD fantoir2 text; /* utilisé pour mémoriser les rapprochements */
UPDATE ign_group SET fantoir2 = null, id_fantoir = code_insee||id_fantoir;

/* nettoyage préalable de FANTOIR (double espaces, trait d'union, apostrophes) */
update dgfip_fantoir set libelle_voie=regexp_replace(libelle_voie,E'([\'-]|  *)',' ','g') WHERE libelle_voie ~ E'([\'-]|  )';
update dgfip_fantoir set libelle_voie=regexp_replace(libelle_voie,E'([\'-]|  *)',' ','g') WHERE libelle_voie ~ E'([\'-]|  )';
update dgfip_fantoir set libelle_voie=regexp_replace(libelle_voie,E'([\'-]|  *)',' ','g') WHERE libelle_voie ~ E'([\'-]|  )';
update dgfip_fantoir set dernier_mot = '0 0 0 0' where dernier_mot = '*';
update dgfip_fantoir set nature_voie='ALL', libelle_voie=substr(libelle_voie,5) where nature_voie = '' and libelle_voie like 'ALL %';
update dgfip_fantoir set nature_voie='RUE', libelle_voie=substr(libelle_voie,5) where nature_voie = '' and libelle_voie like 'RUE %';
update dgfip_fantoir set nature_voie='AV', libelle_voie=substr(libelle_voie,4) where nature_voie = '' and libelle_voie like 'AV %';

/* rapprochement sur libellés IGN ou AFNOR identique à FANTOIR une fois le type de voie désabrégé */
WITH u as (
select i.id_pseudo_fpb as id_fpb, i.nom, i.nom_afnor, f.nature_voie, f.libelle_voie, max(f.fantoir2) as fantoir, string_agg(distinct(f.fantoir2),',' ORDER BY f.fantoir2) as fantoirs
from ign_group i
left join dgfip_fantoir f on (f.code_insee=i.code_insee and (upper(unaccent(replace(replace(replace(i.nom,'œ','oe'),'-',' '), E'\'' ,' '))) ~ dernier_mot or nom_afnor ~ dernier_mot)) left join abbrev on (txt_court=f.nature_voie)
where (nom_afnor in (trim(txt_long||' '||f.libelle_voie), trim(f.nature_voie||' '||f.libelle_voie)) or upper(unaccent(replace(replace(replace(i.nom,'œ','oe'),'-',' '), E'\'' ,' '))) in (trim(txt_long||' '||f.libelle_voie), trim(f.nature_voie||' '||f.libelle_voie))) and i.id_fantoir is null
group by 1,2,3,4,5 order by 1
) UPDATE ign_group SET id_fantoir = fantoir, fantoir2=fantoirs from u where id_pseudo_fpb=id_fpb;


/* rapprochement sur libellés IGN ou AFNOR identique à FANTOIR sans type de voie (lieu-dit) */
WITH u as (
select i.id_pseudo_fpb as id_fpb, max(f.fantoir2) as fantoir, string_agg(distinct(f.fantoir2),',' ORDER BY f.fantoir2) as fantoirs
from ign_group i
join dgfip_fantoir f on (f.code_insee=i.code_insee and (f.libelle_voie=upper(unaccent(replace(replace(replace(i.nom,'œ','oe'),'-',' '), E'\'' ,' '))) or f.libelle_voie = regexp_replace(i.nom_afnor,'^(LIEU DIT|LD) ','')))
where i.id_fantoir is null
group by 1 order by 1
) UPDATE ign_group SET id_fantoir = fantoir, fantoir2=fantoirs from u where id_pseudo_fpb=id_fpb;

/* rapprochement sur libellés IGN ou AFNOR identique à FANTOIR sans type de voie (lieu-dit) en éliminant les points cardinaux */
WITH u as (
select i.id_pseudo_fpb as id_fpb, max(f.fantoir2) as fantoir, string_agg(distinct(f.fantoir2),',' ORDER BY f.fantoir2) as fantoirs
from ign_group i
join dgfip_fantoir f on (f.code_insee=i.code_insee and (regexp_replace(f.libelle_voie,' (NORD|SUD|EST|OUEST)$','') in(upper(unaccent(replace(replace(replace(i.nom,'œ','oe'),'-',' '), E'\'' ,' '))),regexp_replace(i.nom_afnor,'^(LIEU DIT|LD) ',''))))
where i.id_fantoir is null
group by 1 order by 1
) UPDATE ign_group SET id_fantoir = fantoir, fantoir2=fantoirs from u where id_pseudo_fpb=id_fpb;


/* libelles nom_afnor non rapprochés */
create table libelles as select nom_afnor as long, trim(regexp_replace(nom_afnor,'^(LIEU DIT |LD )','')) as court from ign_group group by 1,2;
create index libelle_long on libelles (long);

/* libelles nom IGN non rapprochés */
insert into libelles select nom as long, trim(regexp_replace(replace(trim(upper(unaccent(replace(replace(replace(i.nom,'œ','oe'),'-',' '), E'\'' ,' ')))),'LIEU DIT ',''),'(^| )((LE|LA|LES|L|D|DE|DE|DES|DU|A|AU|ET) )*',' ','g')) as court from ign_group i left join libelles l on (long=nom) where long is null group by 1,2;
/* libelles nom FANTOIR */
insert into libelles select trim(nature_voie||' '||libelle_voie) as long, trim(regexp_replace(replace(trim(nature_voie||' '||libelle_voie),'LIEU DIT ',''),'(^| )((LE|LA|LES|L|D|DE|DE|DES|DU|A|AU|ET) )*',' ','g')) as court from dgfip_fantoir f left join libelles l on (long=trim(nature_voie||' '||libelle_voie)) where long is null group by 1,2;
/* libellés RAN */
insert into libelles select lb_voie, lb_voie from ran_group left join libelles on (long=lb_voie) where long is null group by 1,2;
/* suppression des articles */
update libelles set court = regexp_replace(court,'(^| )((LE|LA|LES|L|D|DE|DE|DES|DU|A|AU|ET) )*',' ','g');

/* index par trigram sur le libellé court */
create index libelle_trigram on libelles using gin (court gin_trgm_ops);
analyze libelles;

/* libellés: 0 à la place des O */
update libelles set court = replace(replace(replace(replace(replace(replace(replace(replace(court,'0S','OS'),'0N','ON'),'0U','OU'),'0I','OI'),'0R','OR'),'C0','CO'),'N0','NO'),'L0','L ') where court ~ '[^0-9 ][0][^0-9 ]';
/* des * */
update libelles set court=trim(replace(court,'*','')) where court like '%*%';
/* séparation chiffres */
update libelles set court = regexp_replace(court,'([^0-9 ])([0-9])','\1 \2') where court ~ '([^0-9 ])([0-9])';
update libelles set court = regexp_replace(court,'([0-9])([^0-9 ])','\1 \2') where court ~ '([0-9])([^0-9 ])';

/* libélles: chemin départemental -> CD */
UPDATE libelles SET court = regexp_replace(replace(regexp_replace(court,'(^| )(CD |CHE |)?(CH|CHE|CHEM|CHEMIN)\.? (DEP|DEPT|DEPTA|DEPTAL|DEPART|DEPARTE|DEPARTEM|DEPARTEME|DEPARTEMEN|DEPARTEME|DEPARTEMEN|DEPARTEMENT|DEPARTEMENTA|DEPARTEMTAL|DEPARTEMENTAL|DEPARTEMENTALE|DEPTARMENTAL|DEPARMENTAL|DEPARTEMEMTAL|DEPAETEMENTAL|DEPARTEMTALE)($|\.? ((N|NO|NR|NUM|NUMER|NUMERO|N\.|N°)([0-9 ]))?)','\1CD \8'),'CD CD','CD '),'  *',' ','g') WHERE court ~'(CH|CHE|CHEM|CHEMIN)\.? (DEP|DEPT|DEPART|DEPARTEM|DEPARTEMTAL|DEPARTEMENTA|DEPARTEMENTAL|DEPARTE|DEPTARMENTAL)\.?( N)?';
/* libélles: route départementale -> CD */
update libelles set court=regexp_replace(replace(regexp_replace(court,'(^| )(CD |RD |RTE |)?(RTE|ROUTE)\.? (DEP|DEPT|DEPTA|DEPTAL|DEPART|DEPARTE|DEPARTEM|DEPARTEME|DEPARTEMEN|DEPARTEME|DEPARTEMEN|DEPARTEMENT|DEPARTEMENTA|DEPARTEMTAL|DEPARTEMENTAL|DEPARTEMENTAL|DEPTARMENTAL|DEPARMENTAL|DEPARTEMEMTAL|DEPAETEMENTAL|DEPARTEMTAL|DEPARTEMANTAL|DEPATREMENTAL)E?($|\.? ((N|NO|NR|NUM|NUMER|NUMERO|N\.|N°)([0-9 ]))?)','\1CD \8'),'CD CD','CD '),'  *',' ','g') where court ~'(RTE|ROUTE)\.? (DEP|DEPT|DEPART|DEPARTEM|DEPARTEMTAL|DEPARTEMENTA|DEPARTEMENTAL|DEPARTE|DEPTARMENTAL)\.?( N)?';

with u as (select * from abbrev order by length(txt_long) desc) update libelles set court = replace(court,u.txt_long, u.txt_court) from u where court ~ (txt_long||' ');

update libelles set court=trim(court) where court like ' %' or court like '% ';
update libelles set court=regexp_replace(court,'^(LIEU DIT |LD )','') where court ~ '(LIEU DIT |LD )';




/* ajout geométrie sur données DGFiP provenant de BANO */
ALTER TABLE dgfip_housenumbers ADD geom geography;
UPDATE dgfip_housenumbers SET geom = ST_MakePoint(lon,lat);

