[English](ASYNC_OWNED_STRUCT_CAPTURES_CYCLE.md)

# Captures async de structures propriétaires

## Périmètre

Ce lot applique les règles existantes T1/T6, D1/T11, B1/B2/B4a,
ST1/ST5/ST7/ST15, L1/L2/L6, AS2/AS5/AS8/AS9/AS13/AS14 et RT8.
Les brouillons 01, 03, 04 et 05 sont concernés. Aucune décision normative
n'est modifiée.

Une tâche peut recevoir par transfert une structure dont les champs sont des
Int ou des allocations possédées de Int, String, Vector<Int>, Vector<u8> ou
d'autres structures de cette famille. Les champs inline imbriqués utilisent
la disposition existante. Le graphe propriétaire et les adresses sont conservés.
Les lectures de champs Int et A<Int>, les écritures Int par receveur mutable,
les transferts locaux, la transmission à un enfant async et la destruction
complète sont raccordés. Les champs propriétaires ne peuvent pas être extraits
individuellement ; aucun état partiel n'est introduit.

Les captures propriétaires contenant des emprunts, les enums généraux, les
retours async de structures propriétaires et leur passage à un auxiliaire
synchrone depuis async restent à intégrer. Ce périmètre n'est pas présenté
comme la réalisation complète des règles relatives aux agrégats.

## Défauts et corrections

Le cas [initial](../../validation/open-owned-async-struct.crb) était refusé à la
signature async : [baseline](../../validation/owned-async-struct-baseline.log).
La traduction utilise maintenant le graphe Cell et son nettoyage existant.
Les types de structure restent disponibles après un renommage ou transfert.
Les champs String/Vector ne peuvent pas être lus abusivement comme des Int.

Après cette première extension, une fabrique synchrone perdait la provenance
du pool d'un champ possédé. Le
[contre-exemple](../../validation/open-owned-task-factory-short-pool.crb) était
accepté par les deux stages alors que le pool du champ finissait avant la tâche.
Cette acceptation est [conservée](../../validation/owned-task-factory-counterexample.log) ;
le programme invalide n'a pas été exécuté.

La capture concrète conserve désormais toutes les sources et origines de ses
descendants possédés. Le contrat conserve les sources symboliques par chemin
de champ, par exemple `.child/.value`. Les relais composent ces chemins et
les appels les instancient sur le graphe réel. Chaque pool doit survivre à la
tâche, indépendamment du pool de la racine.

Deux autres refus de programmes valides ont été corrigés : un retour synchrone
direct `return <-fabrique(...)` empruntait le traitement des tableaux, et
l'inférence d'un bloc natif ne reconnaissait pas le déréférencement d'un champ
A<Int>. Le retour explicite utilise maintenant la voie propriétaire avant le
nettoyage commun ; les vérifications de type et de provenance restent actives.

## Vérifications

`tests/test_async_owned_struct_captures.py` comporte neuf méthodes. Un modèle
fini indépendant place chacun des trois pools d'un graphe racine → enfant → Int
avant ou dans un bloc interne. La tâche en sort. Les huit dispositions sont
exercées avec un appel direct, une fabrique et un relais : trois programmes
admis, 21 refusés. Aucun corps appelé n'est nécessaire pour vérifier la source
de chaque champ lors de l'instanciation du contrat.

Les autres cas vérifient les transferts explicites, la mutabilité, les lectures,
le dernier usage d'un emprunt de champ avant la capture, l'usage après drop,
le lancement normal ou refusé, la destruction inactive, la préparation des
arguments avant suspension et les champs de collections.

Quatre sondes C possèdent exclusivement une tâche non lancée : état initial,
suspension simple, terminaison et suspension pendant la préparation d'un
argument ultérieur. Elles vérifient les adresses de la racine et du champ,
la destruction enfant avant parent, une seule destruction et le réemploi
des deux slots. Elles n'ajoutent pas d'annulation publique d'une tâche lancée.

Clang C11, pthread, Wall/Wextra/Werror, Wno-unused-function et UBSan fatal.

## Chronologie et résultats

- `validation/owned-async-struct-initial-o0.log` : sept méthodes,
  sept échecs de sous-cas et quatre erreurs ; refus des relais calculés et
  inférence native incomplète. Journal conservé.
- `validation/owned-async-struct-second-o0.log` : sept méthodes, deux erreurs
  natives restantes ; `third-o0.log` : sept méthodes, OK après correction.
- `validation/owned-async-struct-final-o0.log` : huit méthodes, trois échecs
  UBSan provenant du harnais C : le second objet de test était détruit sans
  initialiser son champ propriétaire. Le harnais a été corrigé pour construire
  une structure complète, conformément à ST1/ST15. Ce résultat n'est pas
  attribué au compilateur.
- `validation/owned-async-struct-final-fixed-o0.log` : huit méthodes,
  7,258 s, OK avant ajout de la suspension d'argument préparé.
- `validation/owned-async-struct-complete-o0.log` : huit méthodes, 13,108 s,
  OK avec les quatre états. `owned-async-struct-borrow-o0.log` complète ce
  passage avec la neuvième méthode sur l'emprunt de champ, réussie.
- `validation/owned-async-struct-counted-o2.log` : neuf méthodes, 8,999 s,
  OK ; 20 exécutions natives et 32 programmes invalides contrôlés par les
  deux stages, soit 64 contrôles de refus.

La première campagne de cinq mutations en détectait quatre. L'oubli de
nettoyage d'une capture préparée survivait, car la tâche était reprise jusqu'à
la terminaison. L'ajout de la sonde suspendue détecte cette faute par le slot
resté occupé. Le journal initial est conservé dans
`validation/owned-async-struct-mutations-o2.log`.

`validation/owned-async-struct-mutations-final-o2.log` : baseline de huit
méthodes, 8,785 s, OK ; cinq mutations détectées : perte de source concrète,
perte de source symbolique, perte lors de l'instanciation, refus du champ
propriétaire natif valide et oubli du nettoyage préparé. Campagne terminée
avec code 0. L'ajout ultérieur du test d'emprunt ne modifie pas ces oracles.

La régression initiale O2 exécute 67 méthodes en 109,161 s : 66 réussissent,
une conserve deux assertions de refus devenues obsolètes. Cet échec est aussi
reproduit sur la copie du compilateur antérieure au lot, dans
`validation/owned-async-struct-boundary-baseline.log`.
Le remplacement de champ mutable est déjà couvert par ST10/ST12 et le
[cycle de terminaison mutable](MUTABLE_FIELD_COMPLETION_CYCLE.md).
Le test est actualisé avec exécution normale, échec de lancement et refus
d'accès à la nouvelle cible pendant l'exécution. Le test corrigé et les dix
méthodes de terminaison mutable passent à O2 en 15,363 s :
`validation/owned-async-struct-boundary-final-o2.log`.

La régression consolidée dans
`validation/owned-async-struct-regression-final-o2.log` passe 76 méthodes à O2,
en 115,025 s, sur le code final et les attendus corrigés. Elle inclut les blocs
natifs, captures de structures par référence, champs références, fabriques,
retours directs d'allocations, Result propriétaires attendus et les neuf
méthodes du présent lot. Processus terminé avec code 0. Aucun processus de ce
lot ne reste actif. Les sélections se recouvrent ; leurs nombres ne sont pas
additionnés comme une couverture indépendante.

## Limites

Le prochain refus de programme valide est conservé dans
[le retour de structure propriétaire](../../validation/open-owned-async-struct-return.crb),
avec les diagnostics des deux stages dans
`validation/owned-async-struct-return-baseline.log`. Les fichiers Python modifiés
et les nouveaux tests passent `py_compile`. Les diffs des trois modules principaux
sont conservés dans `validation/owned-async-struct-*.py.patch`.

Les modèles et les sondes sont finis. Les types et opérations non raccordés
restent ouverts, notamment les retours d'agrégats propriétaires et les captures
de graphes contenant des emprunts. Les retours calculés synchrones ne sont
pas vérifiés pour toutes les compositions possibles. Aucun résultat ASan/TSan
ni preuve générale de sûreté n'est ajouté. Les arbitrages de handles capturés
et de perdantes Select restent distincts de ce lot.
