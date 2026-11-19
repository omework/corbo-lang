[English](ASYNC_VECTOR_PUSH_NEW_CYCLE.md)

# Cycle — push_new et emprunts de cases dans les tâches

## Règles et modification

Pas de changement normatif. AGENTS.md, VALIDATION_GUIDELINES.md, l’index
des sept brouillons et les clauses pertinentes de LANGUAGE_RULES.md,
FOUNDATIONS_AND_VECTORS.md et ASYNC_MULTITHREAD_RULES.md ont été relus.
VE6 impose l’initialisation par défaut avant publication de l’emprunt ;
B1/B2/B4a, F4, AS2/AS9/AS15 imposent la provenance durable, l’exclusivité,
le dernier usage et la conservation des captures pendant une suspension.
VE1/GR1/GR2 portent sur l’identité et les deux sens de croissance.
L’extension normative async prévaut sur le périmètre synchrone historique
de l’introduction des guidelines.

Le contre-exemple `validation/open-async-vector-push-new.crust` est désormais
exécuté et produit 0, 23, 1, 23. Son log de refus antérieur reste historique.
Le lowering accepte une liaison ou un retour direct de `push_new()` sur
Vector<Int/u8>. Le runtime existant initialise la case avant de rendre son
adresse. Le cadre conserve un pointeur du type exact et le vérificateur
réserve la source jusqu’au dernier usage, y compris dans les continuations,
les captures et les retours de tâches enfants. Les références vers un
vecteur reçu par transfert ne peuvent pas s’échapper de son cadre.

La traduction de `&mut u8` est maintenant distincte de celle de `&mut Int`
dans les captures, états, attentes, bras et résultats de join. Un champ
`uint8_t *` dédié évite d’écrire un pointeur d’octet dans un objet C de type
`int *`. Les contrats synchrones conservent le type et la provenance de la
case retournée par join, puis relayée à leur appelant. Le réemprunt partagé
`&*cell` conserve l’emprunt mutable ancêtre : le parent reste réservé jusqu’au
dernier usage de la vue ou de la tâche qui la capture.

## Scénarios et oracles

`tests/test_async_vector_push_new.py` comprend quinze méthodes :
24 exécutions natives normales, deux arrêts contrôlés pour capacité et
31 refus statiques attendus par passage complet.

- Int/u8 sur les deux fronts, avec vérification de la direction réellement
  choisie dans le C ; les cases voisines restent intactes après l’écriture.
- Zéro observable avant écriture, maintien de la valeur après yield,
  puis croissance après le dernier usage de l’emprunt.
- Réservation du vecteur contre lecture, nouvelle insertion, remove et
  second push_new tant que l’emprunt initial est encore utilisé.
- Réemprunt mutable, enfant suspendu, deux relais de retour, join dans
  un appelant synchrone et attente d’un handle dans un parent async.
- Contrat synchrone qui retourne la case de join, avec retour distinct
  dans chaque bras ; destruction prématurée de sa source refusée.
- Réemprunt partagé d’octet, capture inactive et retour d’une vue partagée,
  mutations du parent ou du vecteur refusées avant le dernier usage.
- Branches, boucle, continue, break, écriture `*cell = valeur` et `.set()`.
- Deux modèles indépendants sous forme de listes Python, graines 817 et
  810 : seize insertions par type, longueur et chaque contenu comparés.
- Limite réelle de région 1 Mio, deux tailles d’élément : arrêt avant
  l’impression suivant push_new, sans diagnostic UBSan.
- Source possédée par la tâche, lecture avant drop, puis réemploi du même
  slot après join ; drop avant la dernière lecture et réusage après drop refusés.
- Mauvais types, annotation, arité, mutabilité, débordement de littéral u8
  et échappement d’une référence vers une capture possédée refusés.

Les sorties attendues et les listes ne sont pas calculées depuis les
structures internes du compilateur. Le contrôle de direction dans le C
vérifie une précondition du test, pas la valeur attendue. Le réemploi à
adresse identique ne constitue pas une preuve générale de destruction unique.

## Défauts et ajustements découverts

Le premier lot a exposé une liaison issue de await dont le marqueur mutable
n’était pas enregistré ; cette métadonnée est maintenant conservée. Le test
de front descendant utilisait initialement une région dédiée par valeur et
n’exerçait donc pas le second front : l’annotation a été retirée de ce seul
scénario, en conservant l’assertion sur la direction effectivement obtenue.

Le contrat de retour d’une case après join conservait initialement un
paramètre brut à la place de la provenance de stockage du vecteur. Il est
corrigé et le relais est exécuté. Un ancien test de restriction refusait toute
signature async `&mut u8` ; cette attente a été retirée, car ce refus n’est
pas une règle normative. Les nouveaux tests exécutent les écritures et
exigent les refus de types et de durées de vie invalides. Les autres assertions
de ce test historique restent intactes. Les journaux initiaux sont conservés.

## Preuves exécutées

Configuration native : Clang Homebrew 20.1.3, arm64 macOS, C11, pthread,
`-Wall -Wextra -Werror -Wno-unused-function`, UBSan avec
`-fno-sanitize-recover=all`. Les nouveaux helpers suivent CRUST_TEST_OPT ;
les anciens tests conservent leurs propres paramètres.

| Exécution | Résultat | Trace |
| --- | --- | --- |
| Lot complet O0 | 15 méthodes, 20,917 s, réussi | validation/async-vector-push-new-O0-complete.log |
| O2 avec opérations, remove et résultats de vecteurs | 53 méthodes, 70,537 s, réussi | validation/async-vector-push-new-O2-final.log |
| Emprunts, contrats, tableaux, UTF-8 et voisins synchrones | 44 méthodes, 64,683 s, réussi | validation/async-vector-push-new-neighbors-final.log |
| ABI, résultats typés, états et pools | 15 méthodes, 29,586 s, réussi | validation/async-vector-push-new-abi.log |
| Mutations | Quatre détectées | validation/async-vector-push-new-mutations.log |

Les suites se recouvrent ; ces nombres ne sont pas un total de cas distincts.
La compilation Python des modules modifiés et des trois fichiers de test et
validation a réussi. Le premier passage des voisins comportait l’attente
historique de refus de &mut u8 ; sa trace demeure dans
`validation/async-vector-push-new-borrow-regression.log`.

Les quatre mutations contrôlées dans des copies temporaires sont détectées
par des assertions sémantiques : défaut non nul, réservation du receveur
supprimée, adresse de la première case rendue à la place de la nouvelle,
et provenance du résultat effacée. Trace :
`validation/async-vector-push-new-mutations.log`. Aucun taux global n’est
extrapolé de cet échantillon.

L’essai ASan+UBSan a été interrompu après plusieurs délais dépassés ; il
n’est pas une validation réussie. Un exécutable indépendant ne contenant
que `int main(void){return 0;}` compile avec ASan+UBSan, mais dépasse aussi
dix secondes au lancement sans sortie :
`validation/async-vector-push-new-ASan-smoke.log`. Le mécanisme du délai
n’est pas identifié. La trace partielle reste dans
`validation/async-vector-push-new-ASan.log`. Aucun résultat ASan, TSan,
second compilateur ou preuve formelle n’est revendiqué.

## Limites et suite

Un autre programme valide reste refusé :
`validation/open-join-element-match-expression.crust`. Le relais peut
retourner depuis chaque bras, mais la forme `return match ...` qui produit
l’emprunt est refusée par l’analyse des expressions conditionnelles. La sortie
attendue est 255 ; le diagnostic reproduit est conservé dans le fichier `.log`.
Ce refus reste un écart d’implémentation, pas une décision de langage.

Ce lot n’étend pas les vecteurs async aux propriétaires et aux autres types
d’éléments. Les expressions générales produisant un emprunt et les autres
lignes N/P de la matrice restent à compléter. Reset public reste retiré ;
il n’a pas été réintroduit. Les obligations relatives aux handles publics,
scheduler, threads, Select, mutex et à la data stack implicite restent ouvertes.
Le succès des scénarios exécutés ne prouve ni la sûreté générale ni
l’achèvement des sept brouillons.


Commandes reproductibles :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_vector_push_new -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_vector_push_new test_async_vector_remove test_async_vector_operations test_async_vector_results -v
CRUST_TEST_OPT=-O2 python3 tests/run_async_vector_push_new_regression.py
CRUST_TEST_OPT=-O2 python3 tests/run_plain_join_regression.py
python3 tests/run_async_vector_push_new_mutations.py
```


Mise à jour : le programme `open-join-element-match-expression.crust` est
corrigé dans [REFERENCE_EXPRESSIONS_CYCLE.md](REFERENCE_EXPRESSIONS_CYCLE.md).
La forme conditionnelle dans un corps async reste distincte et ouverte.
