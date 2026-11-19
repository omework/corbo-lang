[English](RECURSIVE_BORROW_PROJECTIONS_CYCLE.md)

# Projections empruntées dans les graphes propriétaires récursifs

## Règles et changements

Application des règles existantes d’accès partagé/mutable, de durée de vie et
de transfert des champs A<T>, en synchrone et dans les états async. Aucun
changement normatif. Le lot poursuit les projections profondes annoncées après
les helpers d’attente récursifs.

Les descendants symboliques ne préparaient que leurs liens propriétaires. Un
helper parcourant plusieurs liens puis lisant un champ &Int était refusé pour
provenance manquante. Les champs empruntés déclarés sont désormais préparés à
la demande sur les seuls descendants explicitement symboliques. Les identités
sont mises en cache par origine et champ ; les valeurs concrètes ne bénéficient
pas de ce mécanisme pour masquer un champ manquant. Les références nominales
gardent le descripteur de sous-structure, y compris l’offset de la cible.

La construction du graphe dans une tâche révélait aussi une perte de prêts :
le transfert d’un propriétaire n’emportait que les chemins énumérés par le type
avant sa première répétition. Les chemins concrets plus profonds sont maintenant
résolus en consommant les composantes du chemin, puis transférés avec le
propriétaire. Le déplacement d’une allocation reste un transfert de responsabilité.

Enfin, le filtre de lecture dans un match reconnaît les lectures ordinaires de
champs, comme il reconnaissait déjà leur déréférencement. Le contrôle normal du
type, de l’existence du champ et des emprunts reste appliqué.

## Défauts reproduits et oracles

Les deux premiers programmes de lecture, synchrones et avec appel depuis une
tâche, étaient refusés pour provenance de champ emprunté manquante.
Après préparation des projections, les lectures étaient exécutables. Le test
négatif async était encore refusé seulement par un usage ultérieur de la
variable déjà dropped. En supprimant cet usage parasite, verify_program et
compile_source acceptaient le drop prématuré avant la lecture du graphe.
La propagation des chemins concrets corrige cette acceptation. Le test négatif
ne réutilise plus la variable ensuite : il isole la dépendance du graphe.

La lecture d’une référence nominale a ensuite révélé le filtre syntaxique de
match, corrigé pour les champs lus. La cible intérieure est précédée d’un Int
valant 99 ; lire le bon champ doit produire 7, pas le début de la racine.

## Cas ciblés

Quatre méthodes dans tests/test_recursive_borrow_projections.py : six exécutions
natives et six programmes invalides aux deux entrées.

- Helper partagé qui suit deux liens propriétaires puis lit &Int, appelé depuis
  main puis depuis un état async après yield ; drop prématuré de la cible refusé.
- Helper mutable suivant les mêmes liens puis écrivant à travers &mut Int,
  en synchrone et depuis async ; écriture directe concurrente de la cible refusée.
- Champ &Point visant une sous-structure intérieure, avec deux chemins d’appel ;
  lecture du bon offset, refus d’écriture de la cible avant le dernier accès,
  puis écriture autorisée après destruction du graphe.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| recursive-borrow-projections-first-o0.log | 2 méthodes, 2 échecs : provenance manquante |
| recursive-borrow-projections-second-o0.log | Lectures passent ; 2 sous-échecs de diagnostic pour le refus trop tardif |
| recursive-borrow-projections-third-o0.log | 2 méthodes, 1,152 s, code 0 |
| recursive-borrow-projections-fourth-o0.log | 3 méthodes, 1,755 s, code 0 |
| recursive-borrow-projections-fifth-o0.log | 4 méthodes, 1 échec du filtre de lecture de champ |
| recursive-borrow-projections-sixth-o0.log | 4 méthodes, 4,615 s, code 0 |

Régressions terminées avec code 0 : 86 méthodes à O2/UBSan en 70,513 s
(validation/recursive-borrow-projections-regression-o2.log) et cinq cas
synchrones O2/UBSan en 3,417 s
(validation/recursive-borrow-projections-sync-regression.log).
Le harnais ciblé compile le C11/pthread, warnings en erreurs, UBSan fatal.
Les cinq cas historiques demandent legacy-reset pour leurs contrôles anciens.

Le programme minimal invalidé est conservé dans
validation/recursive-borrow-target-drop.crust. Les deux diagnostics exécutés
sont dans validation/recursive-borrow-target-drop.log : emprunt actif,
sans dépendre d’un usage ultérieur de la variable déjà détruite.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_recursive_borrow_projections -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_recursive_borrow_projections test_recursive_join_helpers test_recursive_task_factories test_async_recursive_owned test_shared_match_field_reads test_async_stored_views test_async_enum_nominal test_async_owned_borrow_writes test_async_owned_nominal_writes test_async_owned_struct_sync_calls test_async_owned_struct_returns test_public_structure_handles -v
PYTHONPATH=.:tests python3 -m unittest test_foundation_rules.FoundationTests.test_recursive_owned_parameter_can_be_inspected_relayed_and_destroyed test_foundation_rules.FoundationTests.test_recursive_mutable_parameter_updates_deep_leaf_in_place test_foundation_rules.FoundationTests.test_function_returns_consumed_recursive_owned_projection_through_relay test_foundation_rules.FoundationTests.test_recursive_enum_shared_links_match_terminal_variant test_foundation_rules.FoundationTests.test_recursive_enum_match_retains_all_referent_variants -v
``` Les sorties, diagnostics et
règles de durée de vie sont les attentes explicites des tests ; aucun nouvel
oracle indépendant ou campagne de mutations n’a été ajouté.

## Limites

Les opérations exercées sont des lectures et écritures sur les cibles
empruntées, sans remplacement du lien propriétaire. Le retour d’un emprunt
profond depuis le helper et les substitutions de descendants récursifs ne sont
pas déclarés complets par ce lot. Les continuations symboliques restent une
représentation finie des inconnues, pas une preuve de toutes les opérations.
L’objectif global reste ouvert ; pas d’audit indépendant réalisé dans ce lot.

Snapshot : /tmp/crust-before-recursive-borrow-projections/.
Diffs : validation/recursive-borrow-projections-crust.py.patch et
validation/recursive-borrow-projections-async_lowering.py.patch.
