[English](SYNC_VIEW_BRIDGES_CYCLE.md)

# Vues des auxiliaires synchrones dans les états async et natifs

## Périmètre

Ce lot applique B1–B5, D1/D3, AS2/AS8/AS11/AS12, RT5/RT6 et U1 sans
changer leur sémantique. Les appels synchrones depuis un état prennent en
charge &str, &u8, &[Int/u8], &mut [Int/u8] et Result<&str,SliceError> comme
paramètres et résultats. Les arguments sont évalués dans l’ordre ; leurs
emprunts préparés protègent les cibles pendant les arguments suivants, même
si une sous-expression suspend l’appelante. Le contrat du résultat conserve
ses cibles possibles, sans retenir les arguments indépendants après retour.

La représentation C des vues traverse un pont synchrone généré. L’analyse
précoce des résultats et des contraintes consulte aussi les contrats des
auxiliaires : sans cela elle attachait conservativement un résultat à tous
les arguments. Les sous-vues et références d’octets d’un résultat calculé
conservent les emprunts du receveur évalué, y compris pendant l’évaluation
suspendue de l’indice. Les blocs natifs infèrent le type d’une tranche de
String ou Vector capturée sans annotation. Enfin, un appel synchrone faillible
isolé suivi de `;` ne contourne plus U1 dans un corps async.

## Contre-exemples et corrections

`validation/open-public-view-result-helper-precision.crust` était refusé :
une fonction async retournait la vue d’un auxiliaire synchrone. Après le
raccordement du type, la conservation excessive de l’autre argument empêchait
son drop après join. La consultation du contrat corrige cette dépendance.
La fixture initiale avait elle-même un défaut : le drop de scratch depuis un
bras enfant exigeait `scratch ->;`. Cette importation explicite est ajoutée ;
le compilateur continue de refuser le programme sans elle. Les diagnostics
intermédiaires sont conservés dans les journaux initial-probe, precision-probe
et precision-corrected du préfixe `validation/sync-view-bridges-`.

Les tests ont également mis en évidence le manque de suivi des vues calculées
par `&identity(&data[..])[..2]` et de l’inférence de capture native d’une
tranche. Ils couvrent maintenant ces chemins et les voisins invalides : drop,
croissance, écriture incompatible, résultat local non durable et mutation
pendant l’évaluation de l’indice. Aucun cas valide n’est reclassé invalide pour
accommoder une restriction du backend.

Deux corrections de fixtures restent visibles : une liaison n avait été
redéclarée ; une trace de destruction attendait un texte qui n’est pas celui
du runtime. Le test final exige exactement un événement destroy puis un
événement reclaim, et vérifie que le corps appelé après un return d’argument
ne s’exécute jamais. Il ne dépend pas de la valeur diagnostique imprimée par
destroy pour une String.

## Preuves exécutées

`tests/test_sync_view_bridges.py` comporte douze méthodes. Les onze premières
passent ensemble avec Clang C11, pthread, avertissements fatals et UBSan fatal :

- O0 : 11 méthodes, 11,673 s, `validation/sync-view-bridges-final-complete-o0.log`.
- O2 : 11 méthodes, 12,787 s, `validation/sync-view-bridges-final-complete-o2.log`.

Le complément de captures natives de tranches Vector<Int/u8> passe séparément
à O0 (0,719 s) et O2 (0,869 s), journaux native-slices-o0 et native-slices-o2.
Aucun changement du compilateur n’intervient entre les passages des onze
méthodes et ce complément. La compilation Python des cinq modules modifiés
et de trois fichiers de tests/campagnes réussit.

Les tests exercent les deux modes de tranche, deux types d’éléments, deux
relais synchrones, deux branches de résultat, les suspensions, le dernier
usage, les retours anticipés et le nettoyage. Le résultat de try_slice traverse
un second auxiliaire avant le match : succès, frontière UTF-8 invalide et
indice hors limites sont observés. Un drop explicite du résultat faillible
est admis ; abandon, liaison inutilisée et `_` sont refusés.

Un modèle indépendant énumère les ensembles nécessaires avant et après join :
32 scénarios, six exécutés et 26 refusés par verify_program et compile_source.
Avant join les trois captures sont requises ; après join seuls les deux
arguments susceptibles de fournir le résultat le sont. Les attentes du modèle
ne consultent ni les contrats calculés ni le C généré.

La régression élargie réussit 99 méthodes O2 en 84,721 s :
`validation/sync-view-bridges-regression-o2.log`. Elle couvre appels synchrones
scalaires/empruntés/propriétaires, blocs natifs, handles publics à vues,
try_slice async et expressions empruntées. Ce passage a commencé avant le
dernier contrôle U1 ; ce contrôle est couvert par les passages ciblés finaux.
Il ne s’agit pas de toute la suite du dépôt.

Après le dernier contrôle U1, la régression d’usage propriétaire et de découpes
UTF-8 async passe aussi : 23 méthodes O2 en 36.935 s, journal
`validation/sync-view-bridges-usage-regression-o2.log`.

## Mutations

La campagne finale `tests/run_sync_view_bridge_mutations.py` détecte cinq
fautes dans des copies temporaires du compilateur :

1. Autoriser l’abandon de l’appel faillible : un programme invalide est accepté.
2. Effacer les prêts du résultat : une destruction prématurée est acceptée.
3. Effacer les prêts des arguments préparés : une mutation concurrente à leur
   usage logique est acceptée pendant un argument suspendu.
4. Effacer les prêts d’une sous-vue calculée : sa cible peut être détruite.
5. Ignorer le contrat précis du helper : le modèle voit refuser un drop valide.

Journal : `validation/sync-view-bridges-final-mutations-o2.log`.
La campagne des emprunts d’octets est aussi rejouée : baseline de douze
méthodes réussie puis cinq fautes détectées dans
`validation/sync-view-bridges-byte-mutations-o2.log`. Deux ancres textuelles du
runner sont adaptées au code refactoré ; les défauts injectés ne changent pas.
Les échecs affichés dans ces journaux sont ceux des compilateurs mutés.

## Mise à jour documentaire

La section Limites du README contenait des restrictions historiques désormais
contredites par les cycles exécutés : Bool, résultats empruntés conditionnels,
structures/collections, régions à deux fronts et récursion async scalaire.
Ces affirmations sont remplacées par les périmètres et liens actuels, sans
modifier les règles normatives ni présenter une généralisation comme achevée.

## Limites et suite

Complément ultérieur : les fabriques synchrones de handles et leur attente
dans un état sont maintenant raccordées dans
[SYNC_HANDLE_BRIDGES_CYCLE.md](SYNC_HANDLE_BRIDGES_CYCLE.md), pour les paramètres
et résultats listés dans ce rapport. La limite ci-dessous décrit l’état lors
de ce cycle de vues ; les projections générales restent ouvertes.


Les fabriques synchrones de runtime::Handle<T> appelées depuis un état ne sont
pas raccordées par ce lot. Le contre-exemple
`validation/open-public-view-handle-async-helper.crust` reste ouvert. Son refus
est reproduit sur le compilateur après ce lot dans
`validation/sync-view-bridges-next-handle-probe.log`. Les
paramètres de vues ici traités sont directs ; les projections de toutes les
formes d’agrégats et les références générales de collections ne sont pas
couverts. L’arbitrage sur la capture d’un handle déjà lancé reste en attente.

Select, remplacement public du scheduler, placement statique général et les
autres obligations globales restent ouverts. Reset reste une API historique,
non réintroduite dans le prototype. Aucun résultat ASan/TSan, second compilateur
C ou preuve formelle n’est ajouté. Les modèles et mutations portent sur les
compositions finies décrites ici, sans taux global de sûreté revendiqué.

Snapshot : `/tmp/crust-before-sync-view-bridges`. Les différences des cinq
modules et du runner d’octets sont conservées dans
`validation/sync-view-bridges-*.py.patch`. L’objectif global reste actif.
