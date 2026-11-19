[English](ASYNC_OPTION_JOIN_CYCLE.md)

# Option propriétaire dans l'enveloppe d'un handle

## Règles et périmètre

Application de H1–H2, VE3, U1, B1–B5, AS2–AS5, AS8–AS15, RT6 et SL1–SL2,
sans modification normative. Le lancement d'une tâche retournant Option<A<Int>>
produit un handle dont l'attente restitue Result<Option<A<Int>>,runtime::Error>.
Ok(Some(...)), Ok(None) et Err(...) restent distincts. Le résultat conserve le
pool de l'allocation éventuelle, pas la durée de vie du vecteur qui la contenait.
Les transferts et usages explicites restent requis.

## Implémentation

CrustOptionJoinResult contient un statut externe et un VectorHandleResult.
Sa définition est émise avec les types de valeurs du compilateur ; le runtime
générique reste indépendant de cette enveloppe.
Le nettoyage est conditionné par la réussite externe et la présence interne.
Les transitions de transfert vident le pointeur source ; le receveur en assume
ensuite le nettoyage. Le résultat est raccordé aux signatures, aux contrats de
provenance et de contraintes, aux matchs, aux blocs et aux retours.

Le join synchrone et l'attente async utilisent les primitives existantes de
restitution dans un stockage typé. runtime::Handle<Option<A<Int>>> conserve
un groupe opaque pour la source de son résultat dans les contrats publics.
Les captures et relais de l'enveloppe utilisent le même suivi que les autres
résultats propriétaires. Les arguments préparés avant une suspension sont
enregistrés pour le nettoyage si l'appel n'est finalement pas exécuté.

Un résultat optionnel dont l'ensemble résolu de sources est vide ne possède
aucune allocation. Son enveloppe conserve néanmoins son type de stockage pool,
y compris lorsqu'elle traverse un helper. Cette distinction corrige les deux
défauts rencontrés sur None pendant le lot.

## Cas ciblés et défauts rencontrés

Sept méthodes dans tests/test_async_option_join.py : dix-neuf exécutions natives,
cinq programmes invalides aux deux entrées verify_program et compile_source.

- Succès Some/None et échec de lancement injecté ; sorties et destruction unique.
- Attente async du handle et retour de l'enveloppe par une tâche attendue directement.
- Helper d'attente avec handle public, puis relais synchrone, avec Some et None.
- Drop nommé et direct ; capture dans une tâche inactive puis destruction.
- Pool survivant au vecteur admis, pool local trop court refusé.
- Argument propriétaire préparé avant un await ; nettoyage dans un perdant de Select.
- Transferts par bloc, if et break, avec injection explicite du handle dans le bloc enfant.
- Motif ignorant le contenu, résultat sans usage, flèche absente et réutilisation
  après transfert refusés.

Le premier passage a détecté l'invariant erroné « allocation vivante sans
provenance » pour None. Le test d'échec interne injectait également dans le
mauvais chemin de lancement : il vise désormais la première soumission async,
indépendante de la soumission synchrone qui lance l'appelante. Le troisième
passage a détecté la perte du type de stockage de None dans le helper. Trois
programmes de test omettaient aussi le transfert descendant du handle : leurs
snippets ont été corrigés, sans assouplir la règle de portée de join.

La régression du runtime seul a ensuite révélé que la définition de l’enveloppe
avait été placée dans son module générique alors qu’elle dépendait d’un type
émis par le compilateur. Elle a été déplacée à côté de VectorHandleResult.
Le module async_runtime.py est finalement identique au snapshot antérieur.

## Exécutions

| Journal dans validation/ | Résultat |
| --- | --- |
| async-option-join-first-o0.log | Cinq méthodes, 4,288 s ; deux échecs décrits ci-dessus |
| async-option-join-second-o0.log | Cinq méthodes, 5,885 s, code 0 |
| async-option-join-third-o0.log | Sept méthodes, 6,589 s ; défaut None/helper et trois snippets sans transfert descendant |
| async-option-join-fourth-o0.log | Sept méthodes, 8,415 s, code 0 |
| async-option-join-regression-o2.log | 83 méthodes, 152,442 s, code 0, avant le déplacement de la définition C |
| async-option-join-runtime-before.log | Quatre méthodes en échec de compilation C : VectorHandleResult absent du runtime autonome |
| async-option-join-final-o2.log | Sept méthodes ciblées et quatre du runtime : onze méthodes, 11,856 s, code 0 après correction |

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_option_join -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_option_join test_async_handle_option_results test_async_handle_option_calls test_async_awaited_owned_results test_public_handle_contracts test_public_handle_types test_recursive_join_helpers test_select_source -v
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest test_async_option_join test_task_wakes -v
```

C11/pthread, avertissements en erreurs et UBSan fatal. Les oracles vérifient les
sorties, les destructions et le réemploi des slots. Le modèle existant de
poll/nettoyage de Select est inclus dans la régression. Aucun nouveau modèle
indépendant ni campagne de mutations ; l'audit approfondi reste différé. Ces
résultats ne constituent pas une preuve générale de sûreté. La passe de 83 méthodes
n’a pas été répétée après le déplacement de la définition C : les sept méthodes
ciblées et les quatre du runtime ont été rejouées après cette correction.

## Limites et suite

Le type testé est Option<A<Int>>. L'ajout d'une enveloppe supplémentaire autour
de Result<Option<A<Int>>,runtime::Error> reste non raccordé : une telle tâche
peut être attendue directement, mais son lancement par spawn est encore refusé.
Les autres types génériques ne sont pas couverts par ce lot.

Le cas suivant est conservé dans validation/open-async-handle-vector-replace.crust
et son journal : le remplacement d'un handle de vecteur dans un état async est
refusé aux deux entrées, avec « expression array_handle_exchange non prise en charge ».
try_push, les constructions et autres retours de vecteurs, ainsi que les
arbitrages d'interface déjà ouverts, ne sont pas clôturés ici.

Snapshot : /tmp/crust-before-async-option-join/.
Diffs : validation/async-option-join-*.py.patch (huit fichiers du compilateur).
