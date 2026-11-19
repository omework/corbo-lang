[English](ASYNC_RESULT_RELAYS_CYCLE.md)

# Résultats locaux async : blocs parents et relais entre états

## Règles et implémentation

Ce lot complète ASYNC_RESULT_STORAGE_CYCLE.md pour T1/T6, V4/V5,
L1/L2/L7, B1/B2 et AS2/AS9–AS14. Les règles normatives restent inchangées.
Une valeur locale neuve destinée au parent doit être construite dans son
stockage ; attendre une tâche intermédiaire ne doit ni déplacer cette valeur
ni fermer sa destination. Le placement du résultat ne promeut pas les cibles
empruntées par les captures.

`async_local_placement.result_constructors` suit désormais les appels async
et leur attente à partir des contrats de résultat complets. Un descripteur
interne distingue l'instance de tâche de son résultat. L'analyse propage
l'identité du constructeur à travers les liaisons, branches, scopes et le
point fixe des boucles déjà existant. Elle ne reparcourt pas le corps des
fonctions appelées. Les sources inconnues, résultats contenant des champs
non raccordés et retours d'entrées capturées restent hors de ce nouveau plan.

Le même suivi alimente le placement du résultat d'un bloc, le remplacement
d'un receveur existant et la destination externe d'un résultat de fonction
async. Un appel enfant peut ainsi recevoir directement la destination de son
ancêtre. Il ne devient pas responsable de sa fermeture.

Les sources externes à l'état (captures locales et destination du résultat)
sont classées au-dessus des scopes internes. Un remplacement intermédiaire
ne peut plus raccourcir un placement préalablement établi vers cette source.
La forme explicite `receveur = <- enfant().await` est également raccordée à
la branche de remplacement par résultat attendu. L'ancienne valeur demeure
vivante pendant l'évaluation du remplacement.

Snapshot : `/tmp/crust-before-async-result-relays`. Diffs conservés dans
`validation/async-result-relays-async_lowering.py.patch` et
`validation/async-result-relays-async_local_placement.py.patch`.

## Preuves exécutées et chronologie

- `validation/async-result-relays-initial-o0.log` : 23 méthodes exécutées,
  dont les 14 méthodes du lot précédent découvertes par inadvertance via
  l'import d'une classe de test. Un échec révèle la forme `<- … .await`
  non reconnue dans une affectation. L'import est corrigé en import de module,
  sans retirer de scénario de la suite visée.
- `validation/async-result-relays-corrected-o0.log` : neuf méthodes passent,
  6,888 s, avant les cas de tâche transférée et de remplacement dans un relais.
- `validation/async-result-relays-expanded-o2.log` : neuf méthodes, un échec.
  Le nouveau cas de remplacement dans un relais révèle un raccourcissement
  de la destination externe par le plan d'affectation local.
- `validation/async-result-relays-corrected-expanded-o2.log` : les neuf méthodes
  passent après classement des sources externes au-dessus des scopes internes.
- `validation/async-result-relays-counted-o0.log` : neuf méthodes passent,
  **18 exécutions natives**, **quatre programmes invalides** refusés aux deux
  stages, soit **huit contrôles de refus**, 12,062 s. Aucun skip.
- `validation/async-result-relays-mutations-o2.log` : baseline des neuf méthodes
  réussie en 10,619 s, puis **six mutations détectées**.
- `validation/async-result-relays-regression-o2.log` : **130 méthodes** passent
  sur le code final, 121,940 s, dont les quatorze méthodes du lot précédent.
  Le modèle fini de propagation des producteurs après boucle du lot antérieur
  fait partie de cette sélection.

Tous les processus mentionnés ont un statut terminal observé. Le contrôle
`validation/async-result-relays-remaining.log` confirme les restrictions
résiduelles sur les fabriques et les graphes de résultat.

Les exécutions C utilisent Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function, UBSan fatal, à O0/O2 selon le journal. Les journaux des
échecs initiaux sont conservés. Il n'y a pas de nouveau résultat ASan/TSan.

La suite couvre les exemples enregistrés `open-async-result-storage-child_parent`
et `open-async-result-storage-relay`, transferts successifs, tâche nommée ou
transférée avant attente, branches, boucle avec continue, retours calculés,
chaîne de trois états, remplacements, copie indépendante d'un original de
scope enfant. Les voisins invalides interdisent le drop d'une capture encore
empruntée, la sortie d'une tâche avec capture empruntée trop courte, le résultat
dépendant d'un pool enfant et le drop d'un résultat encore emprunté.

Deux familles de sondes C contrôlent le résultat à des étapes choisies
indépendamment du plan du compilateur. La fermeture du stockage d'un bloc
enfant laisse la cellule du parent vivante à la même adresse. La fin d'un
relais rend ses deux slots d'états avant le dernier usage du résultat. Un
nettoyage interne d'une chaîne suspendue non lancée détruit sa cellule une
fois et ferme sa source une fois, puis les trois pools sont vides. Les sondes
ne lisent pas une cellule après la fermeture de sa source. Les traces de
boucle attendent trois constructions/destructions, dont une valeur remise.

## Mutations

Les fautes retirent respectivement la reconnaissance d'un producteur async,
la propagation par await, la provenance locale d'une entrée copiée, la priorité
de la destination externe et la forme explicite de remplacement. Ces cinq
fautes sont détectées comme refus inattendus de programmes valides.
La sixième remplace le pointeur de destination dans l'état par NULL ; elle
est détectée par l'échec d'exécution de la sonde sous UBSan fatal.
Les oracles restent inchangés dans les copies mutées. Cette campagne ne mesure
pas une couverture générale de toutes les erreurs possibles.

## Limites et suite

Mise à jour : les fabriques décrites ci-dessous sont raccordées dans
[le cycle suivant](ASYNC_RESULT_FACTORIES_CYCLE.md), avec les limites qui y
sont précisées. Cette section conserve le constat de fin de lot.

Les fabriques synchrones de tâches produisant une valeur locale neuve restent
à raccorder (`validation/open-async-result-storage-factory.crust`). Le stockage
caché du futur résultat doit être transmis depuis le receveur de la fabrique,
et non créé dans son scope temporaire.

Les graphes de résultats à champs propriétaires ou empruntés, les retours
après remplacement de champ propriétaire, et les signatures générales gardent
les écarts détaillés dans les rapports précédents. Les alternatives mêlant
résultat neuf et paramètre retourné ne sont pas généralisées par ce plan.

Il s'agit de chemins finis, de sondes et de mutations ciblées ; aucune preuve
formelle ni couverture de tous les ordonnancements n'est revendiquée. Les
obligations des handles lancés et les arbitrages déjà consignés ne changent
pas. L'objectif global reste ouvert.
