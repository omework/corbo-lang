[English](ASYNC_RESULT_FACTORIES_CYCLE.md)

# Fabriques synchrones de tâches et destination du résultat

## Règles et résultat

Ce lot applique AS2/AS3/AS5/AS9–AS14, T1/T6, V5, L1/L2/L7, B1/B2 et
ST10/ST15, ainsi que la distinction T/A<T> des brouillons 03/04/05/07.
Aucune règle normative n'est modifiée.

Une fabrique synchrone peut maintenant retourner une tâche qui construira
une structure locale neuve. La destination du futur résultat vient du
receveur de la fabrique et survit à son retour. Le résultat conserve son
adresse ; il n'est pas alloué au moment de la création inactive de la tâche.
Les exemples enregistrés `open-async-result-storage-factory.crust`,
`open-async-result-factory-async-caller.crust` et
`open-async-result-factory-relay.crust` sont désormais exécutés par les tests.

## Implémentation et invariants

Les contrats distinguent deux origines internes du résultat futur : une
nouvelle destination locale (`task_output`) et une copie dont le stockage
dépend du paramètre (`task_output_parameter`). Cette dernière utilise une
nouvelle destination si l'entrée est locale, ou le pool de l'entrée si elle
vient d'un pool. Ces marqueurs ne constituent pas de nouvelles notations
publiques et ne promeuvent pas une capture locale empruntée.

Les origines traversent les appels de fabriques, les contrats sans corps,
les alternatives et le transfert d'une instance déjà construite. Le suivi
statique des contraintes distingue la destination de copie de l'allocation
originale. Les jonctions du résultat ne mélangent pas T local et A<T>.

Le backend synchrone transmet une source cachée aux producteurs identifiés
par les contrats. Le placement suit aussi une tâche retournée par des blocs
imbriqués. La source n'est pas fermée dans la fabrique. Les paramètres sources
restent distincts des cibles empruntées, qui doivent toujours survivre à la tâche.

L'appel de fabrique depuis un état async utilise un pont C retournant
`CrustTask *`. Il transmet la destination, les dépendances capturées, celles
du résultat et les effets différés. Le pont exporte la tâche au lieu de la
détruire dans son nettoyage local. Les résultats &mut Int et &str conservent
leurs réservations après attente. La création inactive et l'attente demeurent
des opérations distinctes.

L'analyse des effets de terminaison sait maintenant appliquer le contrat
d'une tâche issue de fabrique. Elle réutilise l'analyse de join pour les
origines du résultat, puis rétablit la signature directe et les écritures
finales exactes : un await direct n'a pas de branche LaunchFailed. Les effets
aux suspensions intermédiaires ne sont pas inventés ; ce contrat de suspension
reste explicitement inconnu pour les fabriques non représentées par leurs
captures originales. Cela peut encore refuser certaines compositions Select.

## Défaut trouvé pendant le raccordement

`open-async-factory-field-valid.crust` met à jour `View.data` vers `b` dans
une tâche créée par une fabrique puis attendue par une tâche extérieure.
Son voisin `open-async-factory-field-invalid.crust` détruit `b` après join
avant de lire `View.data` : il doit être refusé.

Avant le raccordement des effets de terminaison, ces deux programmes étaient
refusés comme non pris en charge. Le journal
`async-result-factories-completion-before.log` reproduit ce résultat avec
le module d'effets antérieur et les autres fichiers du lot courant.

Une première tentative d'adaptation appelait une forme await que l'analyse
symbolique synchrone ne traitait pas. Elle produisait une valeur inconnue et
perdait les écritures de champs : le voisin invalide était accepté. Le journal
`async-result-factories-completion-initial.log` conserve cette acceptation
intermédiaire. **Ce programme invalide n'a pas été exécuté.**

Le raccordement corrigé applique les effets finaux et rejette un résultat
symbolique inconnu. `async-result-factories-completion-corrected.log` montre
le programme valide accepté et son voisin refusé pour emprunt encore utilisé.
La suite finale exécute le valide, vérifie le refus dans les deux stages et
exige que le contrat final du champ vise seulement le paramètre `n`.

## Vérifications exécutées

Les chemins sont relatifs à `validation/` :

- `async-result-factories-initial.log` : premier exemple exécuté, sortie 7.
- `async-result-factories-suite-initial-o0.log` : huit méthodes réussies,
  9,866 s, avant le pont depuis async.
- `async-result-factories-regression-initial-o2.log` : 88 méthodes réussies,
  76,140 s, avant le raccordement des fabriques aux états async.
- `async-result-factories-async-initial.log` conserve une erreur Python de
  l'adaptateur d'inférence (argument cache manquant), corrigée ensuite.
- `async-result-factories-expanded-o0.log` : **douze** méthodes, un échec. Le scénario introduisait un pool<Point> local
  dans un état async, encore non raccordé indépendamment des fabriques.
  Le programme minimal est conservé dans
  `open-async-result-factory-local_struct_pool.crust`. Le test d'interaction
  avec un pool utilise maintenant un Point créé dans le pool synchrone et
  transféré à la tâche ; ce n'est pas une validation du pool local manquant.
- `async-result-factories-corrected-expanded-o0.log` : treize méthodes passent,
  9,815 s ; le contrôle des sources conditionnelles suit dans le journal types O2.
- `async-result-factories-regression-final-o2.log` : 191 méthodes réussies,
  165,260 s, **avant** le complément des effets de terminaison et des vues UTF-8.
  Le nom du journal est historique et ne désigne pas le dernier état du lot.
- `async-result-factories-counted-final-o0.log` : **16 méthodes**, **35 exécutions
  natives**, **neuf programmes invalides** refusés aux deux stages, soit
  **18 contrôles de refus**, 20,660 s. Aucun skip.
- `async-result-factories-mutations-final-o2.log` : baseline des seize méthodes
  réussie en 21,041 s, puis **huit mutations détectées**.
- Régression après le complément de terminaison : **216 méthodes réussies en
  166,544 s à O2**, résultat terminal `OK` dans
  `validation/async-result-factories-completion-regression-o2.log`.

Les compilations natives utilisent Clang C11, pthread, Wall/Wextra/Werror,
Wno-unused-function et UBSan fatal, à O0/O2 selon le journal. Aucun résultat
ASan/TSan nouveau et aucune preuve générale de sûreté ne sont revendiqués.

Les scénarios comprennent les fabriques en chaîne, le transfert d'instance,
les retours conditionnels et de boucle, les copies locales et de pool, les
transferts vers les parents, les appelants sync/async, Select, les résultats
empruntés, le nettoyage inactif, un refus de lancement injecté et deux tâches
lancées. Les branches de copie utilisent un oracle simple : 7 pour l'entrée A,
9 pour B ; les deux entrées peuvent avoir un stockage local ou de pool mais
pas des types de stockage différents pour un même résultat.

La sonde C fournit elle-même une source externe à la fabrique. Avant poll,
aucune cellule n'est créée et aucune source fermée. Après suspension, la cellule
appartient à cette source. Après remise, elle reste à la même adresse et le
pool de l'état est vide. Après destruction normale ou nettoyage interne d'une
instance non lancée suspendue par poll, la cellule est détruite une fois,
le curseur revient à zéro et seule la sonde ferme la source. Il ne s'agit pas
d'une API d'annulation de tâche lancée.

## Mutations

Les huit fautes retirent l'origine du résultat futur, sa conservation au
transfert d'une tâche, la distinction de source d'une copie locale, la
transmission de destination, l'export de la tâche du pont, le pointeur de
destination au runtime, la précision des écritures finales de champs et la
réservation d'une vue UTF-8 retournée.

Les premières fautes sont détectées par refus inattendus ou assertions sur
les contrats. La tâche détruite dans le pont échoue à l'exécution avec
`invalid async await`. La destination NULL est détectée par UBSan fatal.
La mutation de vue est détectée par l'acceptation d'un voisin invalide.
Aucun oracle n'est modifié dans les copies mutées. Les huit détections ciblées
ne constituent pas une estimation globale de couverture.

## Limites et suite

- Les pools de structures créés directement dans un état async restent ouverts.
- Le graphe d'un résultat local neuf avec champs propriétaires ou empruntés et
  la restitution après remplacement d'un champ propriétaire restent à compléter.
- L'analyse des préfixes suspendus des tâches créées par fabrique n'est pas
  encore générale ; certaines compositions Select restent refusées.
- Les signatures/captures plus générales et les arbitrages déjà consignés sur
  les handles lancés restent ouverts. Aucune règle n'est changée pour les contourner.

Snapshot : `/tmp/crust-before-async-result-factories` ; diffs conservés dans
`validation/async-result-factories-*.py.patch`. Les tests, sondes et mutants
sont finis. L'objectif complet des sept brouillons reste ouvert.
