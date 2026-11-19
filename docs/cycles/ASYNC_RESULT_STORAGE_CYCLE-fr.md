[English](ASYNC_RESULT_STORAGE_CYCLE.md)

# Destination des résultats locaux neufs des tâches

## Règles et portée

Ce lot applique T1/T6, V5, L1/L2/L7, B1/B2 et AS2/AS8–AS14,
avec les brouillons 03/04/05/07. Il ne modifie aucune règle normative.
Une structure locale neuve retournée par une tâche doit être construite dans
un stockage qui survit à cette tâche, sans déplacement ultérieur. Une copie
issue d'un pool conserve au contraire ce pool. L'original copié et la source
de stockage de la copie ne sont pas la même dépendance.

Le cas `validation/open-async-fresh-local-result-destination.crust`, refusé au
cycle précédent, s'exécute maintenant et affiche 7. La couverture porte sur
les structures sans champs propriétaires ni champs empruntés prises en charge
par les signatures async existantes. Les autres graphes ne sont pas déclarés
implémentés par ce résultat.

## Implémentation

`async_result_storage.py` déduit, depuis le contrat de résultat complet,
la nécessité d'une destination externe et les paramètres dont les sources
restent nécessaires. Cette décision dépend de l'instanciation statique
locale/pool ; aucun déplacement ou choix de provenance au runtime n'est ajouté.

Les fabriques générées reçoivent une source de destination cachée lorsque la
routine peut produire une structure locale neuve. Les variantes de pool
passent NULL lorsqu'elles n'ont pas besoin de cette destination. Les appelants
synchrones et async retiennent la source jusqu'au nettoyage de l'instance et,
après remise, jusqu'au nettoyage du résultat. La routine emprunte cette source
mais ne la ferme pas. Le plan de placement suit les producteurs des retours,
y compris les retours calculés, branches et boucles. Les copies locales ne
retiennent pas la racine originale comme source de leur résultat ; les copies
de pool conservent sa provenance.

Le stockage local d'une source est maintenant distinct de la génération du
layout d'une structure : créer une tâche n'émet pas un layout inutilisé dans
son appelant. Le dictionnaire des paramètres capturés est aussi distinct des
cibles d'un tableau de références, qui utilisait déjà un nom similaire.

Les diffs contre `/tmp/crust-before-async-result-storage` sont conservés dans
`validation/async-result-storage-*.py.patch`. Le nouveau module et les tests
sont directement consultables dans le projet.

## Vérifications exécutées

- `validation/async-result-storage-suite-initial-o0.log` : dix méthodes,
  trois échecs. Deux étaient des refus du C par `-Werror` (layout inutilisé).
  Le troisième test détruisait l'original dans un bras enfant sans transfert
  descendant ; son scénario a été corrigé en recevant le résultat dans le
  scope parent avant de détruire l'original.
- `validation/async-result-storage-suite-corrected-o0.log` : dix méthodes
  réussies, 5,330 s.
- `validation/async-result-storage-expanded-o2.log` : quatorze méthodes
  réussies avant l'ajout du voisin de pool au test des tableaux de références.
- `validation/async-result-storage-counted-final-o0.log` : quatorze méthodes,
  **20 exécutions natives**, **3 programmes invalides**, chacun vérifié dans
  les deux stages (**6 contrôles de refus**), 16,990 s. Aucun skip.
- `validation/async-result-storage-mutations-final-o2.log` : baseline finale
  des quatorze méthodes réussie, 16,969 s, puis cinq mutations détectées.
- `validation/async-result-storage-runtime-mutation-o2.log` : sixième mutation
  détectée par UBSan fatal à l'exécution.
- `validation/async-result-storage-regression-o2.log` : sélection initiale de
  70 méthodes réussie, 55,826 s, avant les corrections finales.
- `validation/async-result-storage-regression-final-o2.log` : **116 méthodes**
  réussies sur le compilateur final, 115,974 s. Les seuls changements pendant
  ce passage concernent les tests ciblés de ce lot, absents de cette sélection.

Tous les processus de ces passages sont terminés avec un statut terminal
observé. Les campagnes initiales échouées sont conservées séparément.

Les exécutions natives utilisent Clang C11, pthread, `-Wall -Wextra -Werror
-Wno-unused-function`, UBSan avec `-fno-sanitize-recover=all`, aux niveaux
`-O0` et `-O2` indiqués dans les journaux. Aucun résultat ASan/TSan nouveau.

Les scénarios couvrent : appelants sync/async, copies locales et de pool,
retours conditionnels/calculés/imbriqués, boucle avec continue et break,
réemploi, emprunt du résultat puis drop admis/refusé, capture de tableau de
références, deux créations sur threads natifs, échec injecté de lancement et
destruction d'une instance inactive. Trois programmes invalides protègent
respectivement l'emprunt capturé, le pool du résultat et un emprunt du résultat.

Deux sondes C observent le stockage indépendamment du calcul de placement :
la cellule reste à la même adresse, vivante, après libération du slot de
l'enfant ; la source du receveur ne ferme qu'à la fin de sa propre vie.
La seconde sonde détruit une arborescence non lancée mais suspendue par poll,
et exige une destruction et une fermeture uniques, avec les deux pools d'états
vides. Ce contrôle interne ne crée pas d'API publique d'annulation.

## Mutations et contre-exemples

La première campagne conserve deux détections, deux résultats non concluants
et une survivante. Les deux résultats non concluants étaient des refus du
compilateur avant les sondes : le harnais ne les classait pas comme échec
d'acceptation d'un programme valide. Le wrapper local signale maintenant ces
refus comme assertions explicites, sans modifier l'oracle de stockage.

La survivante effaçait les provenances capturées avant un argument tableau de
références. Le test initial plaçait ce tableau en premier et n'utilisait qu'une
copie locale indépendante de l'original. Le test final place le paramètre
structure avant le tableau et exerce les deux provenances locale et pool.
La mutation est alors détectée. Les journaux initiaux sont préservés.

Les six fautes ciblent le drapeau de destination, le suivi des producteurs
retournés, la provenance d'une copie de pool, la fermeture indue de la source
externe, la table des paramètres capturés et le pointeur de destination au
runtime. Les cinq premières sont détectées par le refus inattendu de programmes
valides ; la sixième provoque un diagnostic UBSan d'accès à une source NULL.
Il ne s'agit pas d'un taux global de détection des erreurs mémoire.

`validation/async-result-storage-pool-before.log` réexamine le programme de
pool trop court avec les fichiers du snapshot précédent : les deux stages
le refusaient déjà, avec un diagnostic d'invariant interne sans provenance.
Ce lot n'est donc pas présenté comme corrigeant une acceptation dangereuse
antérieure de ce programme.

## Écarts encore ouverts

Mise à jour ultérieure : le résultat local à champs propriétaires et ses graphes
finis sont raccordés dans [le cycle des graphes locaux](ASYNC_LOCAL_OWNED_RESULT_GRAPHS_CYCLE.md).
Le résultat local à champs empruntés reste ouvert.

Mise à jour : les deux premiers cas ci-dessous sont raccordés et exercés dans
[le cycle suivant](ASYNC_RESULT_RELAYS_CYCLE.md). La liste conserve le constat
à la fin de ce lot.

Les programmes minimaux et diagnostics sont conservés dans
`validation/async-result-storage-exploration.log` et
`validation/async-result-storage-aggregate-gaps.log` :

- `open-async-result-storage-child_parent.crust` : résultat attendu dans un
  bloc puis transféré au parent ; destination du créateur à propager.
- `open-async-result-storage-relay.crust` : résultat neuf relayé par une
  deuxième tâche ; contrat de destination à propager entre états.
- `open-async-result-storage-factory.crust` : fabrique synchrone retournant
  une tâche qui produira un résultat neuf ; stockage caché à placer chez son
  receveur, pas dans le scope de la fabrique.
- `open-async-result-storage-owned.crust` : nouvelle racine avec champ
  propriétaire ; sources des descendants à conserver indépendamment de la racine.
- `open-async-result-storage-borrowed.crust` : nouvelle racine avec champ
  emprunté ; signature et dépendances de résultat encore non raccordées.

La restitution après remplacement d'un champ propriétaire reste également
ouverte (`open-async-return-replaced-owned-field.crust`). Ces programmes ne
sont pas transformés en tests de refus normatifs : leurs restrictions actuelles
sont des écarts d'implémentation. Les cas où une véritable cible empruntée ou
un pool disparaît restent interdits, sans promotion implicite.

Les sondes et séquences sont finies, sans preuve formelle ni validation de tous
les ordonnancements. L'objectif complet des sept brouillons reste ouvert.
