[English](TYPED_VECTOR_EXCHANGES_CYCLE.md)

# Résultats typés de replace et try_push

## Réalisation

VE3–VE4, H1–H3, U1, F2–F4 et B1–B5 s'appliquent désormais aux résultats
synchrones testés de Vector<A<Point>>, Vector<A<String>> et des vecteurs de
handles de Vector<Int>/Vector<u8>. Aucune règle normative n'est modifiée.

`handle_exchange_types.py` reconnaît et construit les deux formes :
`Result<A<T>,A<T>>` pour replace et `Result<(),A<T>>` pour try_push. Le type T
est conservé par le parseur, les analyses de contrats, les paramètres symboliques,
les extractions de bras et les jonctions de résultats. La vérification d'une
signature contrôle aussi que sa charge appartient aux types pris en charge.

Les deux bras conservent séparément leurs sources et identités. Un résultat reçu
par paramètre peut restituer son handle sans confondre stockage local et pool.
Le stockage d'une charge A<T> est connu comme provenant d'un pool ; une annotation
locale T ne peut pas le convertir implicitement. Le C utilise toujours
VectorHandleResult et Cell* : le type statique ne change pas leur layout.
Le nettoyage de try_push reste conditionné à la présence du handle rejeté.

Le refus temporaire de replace/try_push non Int est retiré. En revanche, une
signature async de ces nouveaux résultats reçoit encore un diagnostic explicite
de fonctionnalité non raccordée, avant toute tentative d'enveloppe runtime.
Les signatures async historiques à charge A<Int> restent prises en charge.

## Validation ciblée

Neuf méthodes dans `tests/test_typed_vector_exchanges.py` exécutent 30 programmes
natifs et neuf programmes invalides aux deux entrées, verify_program et
compile_source.

- replace : succès et indice invalide, résultat direct, nommé, annoté ou déplacé.
- Fonctions : retour de résultat, relais, consommation d'un résultat injecté et
  restitution du handle de chacun de ses bras.
- Nettoyage direct avec drop, résultat de if et de loop/break.
- Match consommant immédiat, ainsi que traitement différé du résultat nommé.
- String et vecteurs numériques : charge typée restituée, lue, détruite puis
  slots réutilisés, pour les deux issues de replace.
- try_push : succès et refus à la limite réelle d'une région de 1 Mio, contrat,
  relais, match et destruction directe du résultat. Les cases de remplissage
  utilisent des Point ; le nombre est calculé avec la taille du pointeur hôte.
- Retour du seul bras durable au-delà du scope de l'autre pool ; variante
  remplaçant la source durable par le pool court refusée.
- Refus des flèches absentes, résultat sans usage, double consommation, annotation
  de mauvais résultat/type, motif propriétaire ignoré et annotation locale T
  appliquée à un handle A<T> extrait.

Les sorties et destructions uniques des Point nommés sont contrôlées ; les pools
à capacité un/deux sont réutilisés après nettoyage. Pas de nouvelle recherche
adversariale approfondie, de génération aléatoire ou de campagne de mutations.
Les tests ciblés utilisent C11/pthread, Wall/Wextra/Werror, UBSan et
`-fno-sanitize-recover=all`. Un diagnostic sanitizer fait échouer le test.

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_typed_vector_exchanges -v
```

`validation/typed-vector-exchanges-targeted-sixth-o0.log` : neuf méthodes,
11,012 s, code 0.

## Régressions

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O2 python3 -m unittest \
 test_typed_vector_exchanges test_typed_handle_vectors test_storage_requirements \
 test_async_handle_vector_replace test_async_handle_vector_try_push \
 test_async_handle_exchange_calls test_async_handle_exchange_results \
 test_async_exchange_join test_async_nested_exchange_join -v
```

`validation/typed-vector-exchanges-regression-o2.log` : 78 méthodes,
86,134 s, code 0, O2/UBSan. Les régressions conservent notamment les échecs
runtime injectés et les enveloppes async imbriquées historiques à charge Int.
Elles ne valident pas encore les mêmes enveloppes pour les nouvelles charges.

## Traces de développement

- `validation/typed-vector-exchanges-first-o0.log` : le programme Point auparavant
  refusé s'exécute après propagation du type dans l'enveloppe locale.
- `targeted-o0` : les programmes natifs passent ; l'oracle d'un refus attendait
  un autre libellé que « mode attendu ». Il vérifie désormais ce diagnostic réel.
- `targeted-second-o0` : les nouveaux snippets de charges grandissantes
  redéclaraient un nom ; noms distincts ajoutés sans modifier les valeurs attendues.
- `targeted-third-o0` : huit méthodes passent, 10,462 s.
- `consumer-first-o0` : stockage d'une charge issue d'un résultat paramètre non
  raccordé ; corrigé dans l'analyse des exigences de stockage.
- `targeted-fourth-o0` : le paramètre symbolique du backend n'indiquait pas le
  type de son pool ; corrigé. Une construction de test négatif n'avait pas modifié
  le snippet visé et a été corrigée.
- `targeted-fifth-o0` : le retour historique `-> <- Point` accepte encore une
  charge A<Point> extraite. Cet écart de distinction T/A<T> n'est pas résolu
  par ce lot. Le programme accepté est conservé séparément (voir ci-dessous).
  La suite ciblée contrôle aussi l'annotation explicite `let local:Point=<-n`,
  qui est refusée ; ce test distinct ne remplace pas la vérification manquante
  de la signature. Aucune règle normative n'est modifiée pour autoriser le cas.
- `targeted-sixth-o0` : neuf méthodes passent, avec l'extraction depuis paramètre
  et le refus de conversion implicite de stockage par annotation explicite.

Le programme initial est conservé dans `validation/open-typed-vector-exchange.crust` ;
son ancien diagnostic est conservé dans le log homonyme. Le C désormais généré
est `validation/typed-vector-exchange-point.c`. Les différences avec la sauvegarde
avant ce lot sont archivées dans `validation/typed-vector-exchanges-*.patch`.

## Limites et suite

La distinction entre les retours de structures locales T et d'allocations A<T>
n'est pas systématiquement imposée par les anciennes signatures `-> <- T`.
Le cas observé dans ce lot est conservé dans
`validation/open-plain-structure-return-from-handle-result.crust/.log` : accepté
aux deux entrées malgré son retour Point contenant un A<Point>. V1/T6 et H1
conservent la distinction des types ; l'acceptation actuelle ne fait pas autorité
sur leur sémantique. Ce contrôle de signature reste à compléter. La source et sa
durée de vie restent suivies dans ce cas, mais cela ne prouve pas le respect du
type public annoncé. Les neuf refus comptés ne couvrent pas cet écart ouvert.

Les résultats async/runtime typés au-delà d'A<Int> et les charges contenant des
champs propriétaires ou empruntés restent à raccorder. Les tests sur Point ne
couvrent pas tous les enums, structures ou conteneurs imbriqués. Le retour de
`Option<A<Point>>` depuis une fonction est encore refusé : programme et diagnostic
aux deux entrées dans `validation/open-typed-vector-option-contract.crust/.log`.
Ce refus constitue le prochain écart d'implémentation, pas une restriction normative.

Les cas exécutés donnent des preuves locales ; ils ne prouvent pas la sûreté de
l'ensemble du langage. L'audit indépendant est distinct et reste à organiser
avec l'autre agent dans la passe ultérieure demandée par l'utilisateur.
