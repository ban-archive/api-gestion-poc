
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


/* désabréviation et nettoyage des libellés */
ALTER TABLE dgfip_fantoir ADD nom text;
UPDATE dgfip_fantoir SET nom = trim(nature_voie||' '||libelle_voie);
/* L, D et QU avec apostrophe manquante */
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )L ([AEIOUYH])',E'\\1l\'\\2','g') WHERE nom ~ 'L [AEIOUYH]';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )D ([AEIOUYH])',E'\\1d\'\\2','g') WHERE nom ~ 'D [AEIOUYH]';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )QU ([AEIOUYH])',E'\\1qu\'\\2','g') WHERE nom ~ 'QU [AEIOUYH]';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^PL (PL |PLACE |)','PLACE') WHERE nom LIKE 'PL %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^BD (BD |BOULEVARD |)','Boulevard') WHERE nom LIKE 'BD BOULEVARD%';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^RES (RES |RESIDENCE |)','Résidence') WHERE nom LIKE 'RES %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^RTE (RTE |ROUTE |)','Route ') WHERE nom LIKE 'RTE %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^AV (AV |AVENUE |)','Avenue ') WHERE nom LIKE 'AV %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^SQ (SQ |SQUARE |)','Square ') WHERE nom LIKE 'SQ %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^CHEM (CHEM |CHEMIN |)','Chemin ') WHERE nom LIKE 'CHEM %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^CHE (CHE |CHEMIN |)','Chemin ') WHERE nom LIKE 'CHE %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^RPT (RPT |ROND POINT |ROND )','Rond-Point ') WHERE nom LIKE 'RPT %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^IMP (IMP |IMPASSE |)','Impasse ') WHERE nom LIKE 'IMP %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^ALL (ALL |ALLEE |)','Allée ') WHERE nom LIKE 'ALL %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^RUE (RUE |)','Rue ') WHERE nom LIKE 'RUE %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^GR GR','GR') WHERE nom LIKE 'GR GR%';
UPDATE dgfip_fantoir SET nom = 'GRANDE RUE' WHERE nom in ('GR GRANDE RUE','GR GDE RUE','GR RUE');
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^ACH (ACH |ANCIEN CHEMIN |ANCIEN CHE |ANCIEN CHEM |)','Ancien Chemin ') WHERE nom LIKE 'ACH %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^AUT (AUT |AUTOROUTE |)','Autoroute ') WHERE nom LIKE 'AUT %';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'^ART (ART |ANCIENNE ROUTE |ANCIENNE RTE )','Ancienne Route ') WHERE nom LIKE 'ART %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^BRG (BRG |BRG$|BOURG |BOURG$)','Bourg ')) WHERE nom LIKE 'BRG %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CAN (CAN |CAN$|CANAL |CANAL$)','Canal ')) WHERE nom LIKE 'CAN %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CAR (CAR |CAR$|CARREFOUR |CARREFOUR$)','Carrefour ')) WHERE nom LIKE 'CAR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CHV (CHV |CHV$|CHEMIN VICINAL |CHEMIN VICINAL$)','Chemin Vicinal ')) WHERE nom LIKE 'CHV %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CITE (CITE |CITE$|)','Cité ')) WHERE nom LIKE 'CITE %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CLOS (CLOS |CLOS$|)','Clos ')) WHERE nom LIKE 'CLOS %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^COR (COR |COR$|CORNICHE |CORNICHE$|)','Corniche ')) WHERE nom LIKE 'COR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CD (CD |CD$|)','Chemin Départemental ')) WHERE nom LIKE 'CD %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CF (CF |CF$|CHEMIN FORRESTIER |CHEMIN FORRESTIER$|)','Chemin Forrestier ')) WHERE nom LIKE 'CF %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CR (CR |CR$|CHEMIN RURAL |CHEMIN RURAL$|)','Chemin Rural ')) WHERE nom LIKE 'CR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^CC (CC |CC$|CHEMIN COMMUNAL |CHEMIN COMMUNAL$|)','Chemin Communal ')) WHERE nom LIKE 'CC %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^COUR (COUR |COUR$|)','Cour ')) WHERE nom LIKE 'COUR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^D (D |D$|DEPARTEMENTAL? |DEPARTEMENTAL?$|)','Départementale ')) WHERE nom LIKE 'D %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^DEVI (DEVI |DEVI$|DEVIATION |DEVIATION $|)','Déviation ')) WHERE nom LIKE 'DEVI %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^DOM (DOM |DOM$|DOMAINE |DOMAINE$|)','Domaine ')) WHERE nom LIKE 'DOM %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^DRA (DRA |DRA$|DRAILLE |DRAILLE$|)','Draille ')) WHERE nom LIKE 'DRA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^ECL (ECL |ECL$|ECLUSE |ECLUSE$|)','Écluse ')) WHERE nom LIKE 'ECL %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^ESC (ESC |ESC$|ESCALIER |ESCALIER$|)','Escalier ')) WHERE nom LIKE 'ESC %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^ESP (ESPLANADE |ESPLANADE$|ESPACE |ESPACE$)','\1')) WHERE nom LIKE 'ESP %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^ESPA (ESPA |ESPACE |ESPACE$)','Espace ')) WHERE nom LIKE 'ESPA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^FG (FG |FG$|FBG |FBG$|FAUBOURG |FAUBOURG$)','Faubourg ')) WHERE nom LIKE 'FG %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^FON (FON |FON$|FONTAINE |FONTAINE$)','Fontaine ')) WHERE nom LIKE 'FON %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^GR (GR |)(GRAND |GRANDE )','\2')) WHERE nom LIKE 'GR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^GR ((GR |)GRAND |GRANDE |LA GRANDE )','\1')) WHERE nom LIKE 'GR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^GR (GD|GRD|GR|GR GR|GRDE|GDE) RUE( |$)','Grande Rue ')) WHERE nom LIKE 'GR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^GR (SCO|SCOL|SCOLAIRE) ','Groupe Scolaire ')) WHERE nom LIKE 'GR SCO%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^GR LA (GDE|GRAND) RUE( |$)','La Grand Rue ')) WHERE nom LIKE 'GR %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^HAM (HAM |HAM$|HAMEAU |HAMEAU $|)','Hameau ')) WHERE nom LIKE 'HAM %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^HLM (HLM |HLM$|)','HLM ')) WHERE nom LIKE 'HLM %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^JARD (JARD |JARD$|)','JARDIN ')) WHERE nom LIKE 'JARD %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^LOT (LOT |LOT$|LOT\. |LOT\.$|LOTISS |LOTISS$|LOTISSEMENT |LOTISSEMENT$|)','Lotissement ')) WHERE nom LIKE 'LOT %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^MAIL (MAIL |MAIL$|)','Mail ')) WHERE nom LIKE 'MAIL %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^PARC (PARC |PARC$|)','Parc ')) WHERE nom LIKE 'PARC %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^(PAS|PASS) PASSAGE ','Passage ')) WHERE nom LIKE 'PAS%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^(PAS|PASS) PASSERELLE ','Passerelle ')) WHERE nom LIKE 'PAS%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^PONT PONT ','Pont ')) WHERE nom LIKE 'PONT %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^PROM (PROM |PROM$|PROMENADE |PROMENADE$|)','Promenade ')) WHERE nom LIKE 'PROM %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^QUAI (QUAI |QUAI$|)','Quai ')) WHERE nom LIKE 'QUAI %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^QUA QUARTIER ','Quartier ')) WHERE nom LIKE 'QUA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^ROC ROCADE( |$)','Rocade ')) WHERE nom LIKE 'ROC %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^RUIS (RUIS |RUISSEAU |)','Ruisseau ')) WHERE nom LIKE 'RUIS %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^RLE (RLE |RUELLE |)','Ruelle ')) WHERE nom LIKE 'RLE %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^(SEN|SENT) SENTE ','Sente ')) WHERE nom LIKE 'SEN%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^(SEN|SENT) SENTIER ','Sentier ')) WHERE nom LIKE 'SEN%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^SEN SEN( |$)','SEN ')) WHERE nom LIKE 'SEN%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^SEN SENT( |$)','SENT ')) WHERE nom LIKE 'SEN%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^SEN SENTIER( |$)','Sentier ')) WHERE nom LIKE 'SEN%';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^TRA TRAVERSE( |$)','Traverse ')) WHERE nom LIKE 'TRA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^TRA TRAVERSEE( |$)','Traversée ')) WHERE nom LIKE 'TRA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^TRA TRAVERSO( |$)','Traverso ')) WHERE nom LIKE 'TRA %';
UPDATE dgfip_fantoir SET nom = trim(regexp_replace(nom,'^VCHE LE (VX|VIEUX) (CHEM|CHEMIN)( |$)','Le Vieux-Chemin ')) WHERE nom LIKE 'VCHE %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VCHE( | VCHE|( (VX|VIEUX) (CH|CHE|CHEM|CHEMIN))( |$))','Vieux-Chemin ')),'  ',' ') WHERE nom LIKE 'VCHE %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VC( | VC|( (VOIE) (COMMUNALE))( |$))','Voie Communale ')),'  ',' ') WHERE nom LIKE 'VC %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VEN( | VC|( (VOIE) (COMMUNALE))( |$))','Voie Communale ')),'  ',' ') WHERE nom LIKE 'VC %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VEN(| VENELLE)( |$)','Venelle ')),'  ',' ') WHERE nom LIKE 'VEN %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VLA(| VILLA)( |$)','Villa ')),'  ',' ') WHERE nom LIKE 'VLA %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^ZI(| ZI| ZONE INDUSTRIELLE| ZONE INDUST.)( |$)','Zone Industrielle ')),'  ',' ') WHERE nom LIKE 'ZI %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^ZAC (ZAC )',E'Zone d\'Aménagement Concerté ')),'  ',' ') WHERE nom LIKE 'ZAC %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^ZUP ZUP( |$)','ZUP ')),'  ',' ') WHERE nom LIKE 'ZUP %';
UPDATE dgfip_fantoir SET nom = replace(trim(regexp_replace(nom,'^VOIE VOIE( |$)','Voie ')),'  ',' ') WHERE nom LIKE 'VOIE %';

UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'( |^)AU DSU( |$)','\1au dessus\2') WHERE nom ~ 'AU DSU';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'( |^)AU DSO( |$)','\1au dessous\2') WHERE nom ~ 'AU DSO';

UPDATE dgfip_fantoir SET nom = regexp_replace(nom,' ST ',' Saint-','g') where nom ~ ' ST ';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )CRX( |$)','\1Croix\2','g') where nom ~ 'CRX';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )BD( |$)','\1Boulevard\2','g') where nom ~ 'BD';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )RTE( |$)','\1Route\2','g') where nom ~ 'RTE';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )CHP( |$)','\1Champ\2','g') where nom ~ 'CHP';
UPDATE dgfip_fantoir SET nom = regexp_replace(nom,'(^| )CHPS( |$)','\1Champs\2','g') where nom ~ 'CHPS';
