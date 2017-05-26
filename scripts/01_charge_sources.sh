# Chargement des données sources pour l'initialisation de la BAN
# - INSEE: COG (insee_xxx)
# - IGN: export SGA (ign_xxx)
# - La Poste: export RAN (ran_xxx)
# - DGFiP: FANTOIR et export BANO (dgfip_xxx)
# - Données BANv0 (ban_xxx)
# - Données AITF (aitf_xxx)

cd init
./init_cog.sh
./init_dgfip_fantoir.sh


exit

à compléter !
