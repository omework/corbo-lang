[English](ASYNC_MUTABLE_DESCENDANT_RESULTS_CYCLE.md)

# Retours mutables depuis des descendants possédés

## Périmètre

Les règles existantes d'emprunt mutable, de dernière utilisation, de retour
enfant → parent et AS16 s'appliquent au résultat &mut Int obtenu dans un
descendant A<T>. Le résultat réserve la cible et la capacité d'accès au champ.
Le porteur peut être utilisé de nouveau après le dernier usage du résultat.
Aucune règle normative n'est modifiée.

Le cas enregistré est
`validation/open-async-replaced-mutable-result.crust`. Avant ce lot, il était
refusé lors de l'analyse de la fonction synchrone qui retournait le réemprunt :
« cible empruntée non durable dans le scope parent ».

## Corrections

Un réemprunt d'un descendant possédé conserve maintenant une projection du
paramètre porteur, au lieu d'être décrit par les candidats d'allocation du
descendant comme s'il était local. Il conserve son graphe et son chemin pour
les écritures ultérieures. Le résolveur des contrats reconnaît ce passage par
un champ possédé et réserve la capacité correspondante.

À la création d'une tâche modifiant un champ possédé, les effets de champs
sont préparés sur le graphe proposé après remplacement. Ils ne sont plus
appliqués au descendant ancien. Le contrôle d'exclusivité avait détecté deux
prêts mutables artificiels vers la même cible à cause de cet ancien routage ;
ce contrôle reste inchangé.

La projection du résultat à travers le graphe conserve aussi la réservation
du chemin dans le porteur. Le premier test refusé montrait un écart entre les
entrées : check acceptait une lecture prématurée via un auxiliaire, tandis que
la génération la refusait en parcourant son corps. Les deux entrées refusent
maintenant ce cas depuis les capacités du contrat.

Enfin, les chemins internes `.child/.view` et `.child/view` sont normalisés
de la même manière par le suivi des prêts async, pour que le remplacement du
descendant ne soit pas considéré disjoint de son réemprunt retourné.

## Cas exécutés

Cinq méthodes ciblées comprennent six exécutions natives et neuf programmes
invalides testés aux deux entrées, soit dix-huit contrôles de refus :

- Exemple enregistré et échec de lancement injecté.
- Join, lecture/modification via le résultat et réutilisation du porteur après
  dernier usage ; lecture prématurée du porteur ou écriture de la cible refusée.
- Await direct, drop du porteur et remplacement direct de son descendant refusés
  tant que le résultat reste utilisé.
- Retour depuis une fonction synchrone, avec la même frontière de dernier usage.
- Relais async puis Select, conservation des réservations après drop de Select.

Les valeurs attendues sont 20 après mutation par le résultat et 30 après
destruction du porteur et nouvelle mutation de la cible. Le lancement échoué
n'exécute pas le corps et le programme affiche seulement 30.

O0 ciblé : cinq méthodes, 2,769 s, code 0 ; journal
`validation/async-mutable-descendant-results-relay-o0.log`.
La régression O2 passe 110 méthodes en 89,397 s, code 0 ; journal
`validation/async-mutable-descendant-results-regression-o2.log`. Elle inclut les
cinq méthodes ciblées sur l'état final. Les exécutions natives utilisent Clang
C11, pthread et UBSan sans récupération. Les modèles déjà inclus dans les suites
liées ont été rejoués ; aucun nouveau modèle indépendant n'est revendiqué.

## Limites

Le lot exerce &mut Int dans des structures à descendants suivis. Il ne prouve
pas toutes les alternatives de graphes, les enums récursifs ni les autres
types de cible. Les métadonnées restent conservatrices pour les alternatives
de lancement. Les garanties de sûreté ne se réduisent pas à ces tests.
Pas de nouvelle campagne adversariale ni de mutations ; l'audit indépendant
reste différé selon la consigne utilisateur.

## Reproduction

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_async_mutable_descendant_results -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_async_mutable_descendant_results test_async_replaced_borrow_results test_async_owned_borrow_writes test_async_owned_field_writes test_mutable_field_completion test_borrowed_field_completion test_async_enum_match test_async_consuming_enum_match test_async_enum_suspension_fields test_nested_field_wrappers test_nested_field_choices -v
```

Snapshot : `/tmp/crust-before-async-mutable-descendant-results/`.
Les trois différences sont archivées sous
`validation/async-mutable-descendant-results-{results,crust,async_lowering}.py.patch`.
Les journaux intermédiaires sont conservés, notamment le premier passage qui
expose l'écart check/génération.
