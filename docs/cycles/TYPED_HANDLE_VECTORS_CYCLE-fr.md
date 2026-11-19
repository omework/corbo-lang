[English](TYPED_HANDLE_VECTORS_CYCLE.md)

# Vecteurs de handles typés : opérations synchrones

## Périmètre et règles

Ce lot applique H1–H3, VE1–VE3, B1–B5, F3–F4 et les exigences de stockage
existantes. Aucune règle normative n'est modifiée. Il généralise les opérations
synchrones testées au-delà de Vector<A<Int>> ; il ne termine pas toute la famille
Vector<A<T>>.

Le parseur enregistre les types de vecteurs de handles rencontrés. La vérification,
les contrats de résultat, les effets et les contraintes conservent le type T de
la cible. Le runtime continue de stocker des Cell* ; le pool de chaque cible
assure son nettoyage. Aucun nouveau layout de case ni copie de cible n'est ajouté.

Le constructeur, push, remove, pop local, les paramètres partagés/mutables,
les retours de handles, les relais et les emprunts de cases utilisent maintenant
ce type. Une extraction ne recrée plus un descripteur Int pour une cible Point.
Le remplacement par un emprunt mutable de case contrôle également le type T.
Les slots de handles non Int ont un typedef distinct pour empêcher leur confusion
statique avec A<Int>, tout en conservant la représentation C.

Le suivi de stockage reconnaît qu'une cible extraite d'un Vector<A<T>> provient
d'un pool. Il n'assimile pas cette cible à une structure locale T. Le réemprunt
explicite &mut *v conserve les candidats de provenance de ses éléments.

## Cas exécutés

`tests/test_typed_handle_vectors.py` contient sept méthodes : neuf exécutions
natives et neuf programmes invalides contrôlés chacun par verify_program et
compile_source.

- Point : push, remove, pop/Some, destruction du vecteur encore rempli et réemploi.
- Deux pools : extraction dans l'ordre après transfert du vecteur depuis un bloc.
- Fonctions : insertion injectée, lecture de longueur, extraction et relais par
  réemprunt explicite, avec restitution du A<Point>.
- String, Vector<Int> et Vector<u8> : insertion, extraction, lecture du contenu,
  destruction et réemploi du pool de la cible.
- Emprunt partagé de case typée, comparaison de contenu, remplacement via un
  emprunt mutable, destruction unique de l'ancien et du nouveau contenu.
- Refus : transfert absent, type incompatible, usage après transfert, extraction
  sans flèche, destruction d'un emprunt, pool trop court, conversion implicite
  de Point local en A<Point>, et extraction pendant un emprunt encore utilisé.

Les traces vérifient une destruction pour les Point nommés concernés. Le réemploi
à capacité un vérifie que les slots sont effectivement rendus disponibles. Les
régressions historiques sélectionnées vérifient aussi l'identité des adresses
pour A<Int> ; ce lot ne prétend pas tester toutes les identités pour tous les T.

## Résultats et reproductibilité

Le harness natif utilise C11, pthread, Wall/Wextra/Werror et UBSan avec
`-fno-sanitize-recover=all`. Le contrôle du code retour fait échouer les tests
sur un diagnostic sanitizer.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_handle_vectors -v
```

`validation/typed-handle-vectors-targeted-fifth-o0.log` : sept méthodes,
3,782 s, code 0. Le dernier ajout ultérieur au compilateur est un diagnostic
explicite pour replace/try_push typé encore non raccordé ; l'état final est
exécuté par la régression O2 ci-dessous.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_handle_vectors test_storage_requirements \
 test_async_handle_vector_push test_async_handle_vector_remove \
 test_async_handle_vector_pop test_async_handle_vector_borrows \
 test_async_handle_vector_borrow_returns \
 test_foundation_rules.FoundationTests.test_handle_vector_push_transfers_cleanup_to_vector \
 test_foundation_rules.FoundationTests.test_handle_vector_push_tracks_injected_origins_across_calls \
 test_foundation_rules.FoundationTests.test_handle_vector_borrowed_slot_replacement_tracks_injected_origin \
 test_foundation_rules.FoundationTests.test_handle_vector_remove_preserves_identity_and_frees_origin_after_drop \
 test_foundation_rules.FoundationTests.test_handle_vector_cell_borrows_keep_the_slot_and_its_vector_alive -v
```

`validation/typed-handle-vectors-regression-o2.log` : 59 méthodes, 45,216 s,
code 0. Les suites async, stockage et nouvelle suite utilisent O2/UBSan.
Les cinq méthodes Foundation utilisent leur configuration native historique
(et leur profil legacy-reset explicite), pas CRUST_TEST_OPT. Les modèles déjà
inclus dans les suites sélectionnées sont conservés ; aucun nouveau modèle,
mutation ou programme aléatoire n'a été ajouté.

Le programme initial est conservé dans
`validation/open-vector-allocated-structure.crust`, son refus initial dans le
log homonyme, et le C désormais généré dans
`validation/typed-handle-vector-point.c`. Les différences avec la sauvegarde
précédant ce lot sont archivées dans `validation/typed-handle-vectors-*.patch`.

## Échecs intermédiaires consignés

- `first-o0` : extraction de Some reconstruite en Int, invariant de source violé.
- `second-o0` : premier programme Point exécuté après correction.
- `probes-*` : diagnostics de progression, pas des suites de tests réussies ;
  paramètre typé d'abord inconnu, puis exigence de stockage non raccordée.
- `targeted-o0` : le réemprunt perdait la provenance des éléments ; le test u8
  tentait aussi de l'imprimer sans conversion vers Int. Le snippet a reçu la
  conversion explicite retenue. L'import direct du harness faisait exécuter
  également ses 24 méthodes Select : elles passaient. L'import est corrigé pour
  garder la nouvelle suite ciblée.
- `targeted-second-o0` et `targeted-third-o0` : provenance du réemprunt, puis
  restriction du backend sur le type réemprunté, corrigées sans affaiblir l'oracle.
- `targeted-fourth-o0` : six méthodes, code 0 ; `targeted-fifth-o0` ajoute
  l'emprunt et le remplacement de case typée, sept méthodes, code 0.

## Limites et suite

- Les résultats typés de replace/try_push restent à raccorder. Le programme
  valide `validation/open-typed-vector-exchange.crust` est refusé aux deux
  entrées avec un diagnostic explicite de fonctionnalité manquante, consigné
  dans le log homonyme. Ce refus est un écart d'implémentation, pas une règle.
- Les annotations/signatures Option<A<T>> génériques et leurs enveloppes runtime
  ne sont pas couvertes par le pop local de ce lot.
- Les cibles contenant des champs propriétaires ou empruntés restent refusées
  explicitement : les vecteurs doivent encore propager les métadonnées de ces
  champs. Les enums et structures complexes ne sont pas validés par le seul Point.
- Les opérations async sur ces nouveaux types ne sont pas intégrées par ce lot.
  Les régressions async exécutées portent sur A<Int>.
- Tranches de handles, conteneurs imbriqués de handles, résultats conditionnels
  d'options typées et toutes les combinaisons de types ne sont pas couverts ici.
- Pas de recherche adversariale approfondie ni de mutations dans ce lot, selon
  la priorité utilisateur. La passe indépendante sera faite séparément ; aucun
  résultat de cet audit n'est présumé. Les tests ne sont pas une preuve générale
  de sûreté et le chantier global reste ouvert.
