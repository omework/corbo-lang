[English](ASYNC_INLINE_VECTORS_CYCLE.md)

# Cycle — Structures en ligne dans les vecteurs async

## Règles et portée

VE1–VE4, ST17/ST18, H1–H3, T1/T6, B1–B5/B4a, AS2–AS4,
AS8–AS15 et MT1–MT8 restent inchangées. AGENTS.md, les guidelines complètes
et l’index des brouillons ont été relus, ainsi que les règles concernées.
Ce lot étend aux tâches async le stockage de Vector<Point> déjà raccordé en
synchrone : les cases contiennent les champs de Point, pas des A<Point>.

Le périmètre des layouts reste celui du lot synchrone : structures à feuilles
Int, y compris imbriquées ou vides. Les tests spécifiques de ce lot portent
sur Point à deux champs Int et Empty. Les autres champs et les opérations
encore manquantes de Vector<T> ne sont pas déclarés terminés.

## Implémentation

- Pools locaux et injectés, captures par emprunt mutable ou par transfert,
  paramètres et résultats reconnaissent les vecteurs de structures en ligne.
- Push d’une construction/copie locale alimente les octets de la case puis
  nettoie le temporaire. Copy d’une case et remove produisent une valeur locale
  indépendante ; remove exige le transfert explicite et un receveur mutable.
- L’emprunt du vector reste actif pendant l’évaluation de l’indice, même si
  cette évaluation se suspend. L’indice évalué est conservé dans l’état async.
- Le placement des valeurs locales extraites reconnaît les vecteurs et leurs
  pools. Un résultat transmis au parent ou à l’appelant utilise le stockage
  du destinataire dès sa création, sans déplacement ultérieur d’adresse.
- Les contrats publics Handle et Result reconnaissent A<Vector<Point>>.
  Le relais synchrone conserve la provenance du pool après join.
- Les deux formes AST de len sont raccordées. Aucun changement du runtime C.

## Tests exécutés

Huit méthodes ciblées, **14 exécutions natives réussies**, **8 programmes
invalides vérifiés aux deux entrées** verify_program et compile_source.

- Deux valeurs grandissantes et annotation de région ; copie/extraction lues
  après destruction des vectors et après yield.
- Emprunt mutable capturé : lecture et drop côté appelant refusés avant join.
- Capture propriétaire, attente ou destruction de la tâche inactive, puis
  réutilisation du pool de capacité un. L’ancien nom transféré reste invalide.
- Retour de Point par copie ou extraction, avec await et join ; la signature
  A<Point> est refusée pour ces valeurs locales.
- Vector entier construit dans un pool injecté, contrat public de handle,
  relais du Result, extraction puis réemploi du pool. Un pool enfant trop
  court est refusé.
- Indice fourni par un await, consommation directe de remove par drop,
  résultat d’un if suspendu et structure vide.

Commande ciblée finale :

```sh
PYTHONPATH=.:tests CRUST_TEST_OPT=-O0 python3 -m unittest test_async_inline_vectors -v
```

Résultat : **8 méthodes, 6,324 s, code 0**, journal
validation/async-inline-vectors-targeted-fifth.log. Compilation Clang C11,
pthread, Wall/Wextra/Werror, UBSan fatal. Les sorties attendues sont écrites
indépendamment de l’implémentation ; les invalides ne sont pas exécutés en C.

## Défauts rencontrés et écart conservé

Les premières passes ont identifié l’absence de len sous sa seconde forme AST.
Après correction, les huit méthodes initiales passaient. L’ajout d’un passage
par contrat public a d’abord introduit une erreur de fixture (helper placé
avec une tâche retournant Int), corrigée sans changer la sémantique.

La fixture ajoutée avec `match (->next)` révèle un défaut général distinct :
le parser l’aiguille vers les résultats de replace/try_push, alors que next
est un Result de join. L’analyse perd ensuite le type du contenu de Ok et
refuse remove. Le programme est conservé dans
validation/open-async-inline-public.crust. **Ce cas reste à implémenter**.
Le défaut est aussi reproduit sur un simple Result<Int,runtime::Error> :
validation/open-consuming-join-match.crust et consuming-join-match-baseline.log.
Le test final exerce le même relais avec `match next`, forme déjà prise en
charge pour les résultats de join. Il ne prétend pas valider la notation
consommante explicite. Les journaux first à fourth sont conservés, y compris
les échecs et la réussite intermédiaire antérieure au nouveau cas public.

## Régression et limites

Régression O2/UBSan : **226 méthodes, 215,753 s, code 0**.
Les 31 fichiers de compilateur/test suivis sont restés inchangés pendant
l’exécution (async-inline-vectors-regression-integrity.log).
Sélection : validation/async-inline-vectors-test-selection.txt ; journal :
validation/async-inline-vectors-regression.log. La sélection couvre les
vecteurs synchrones/async, placement local, retours, contrats publics,
Result et exigences de stockage. Elle n’est pas une exécution de toute la suite.

Restent ouverts : champs empruntés/propriétaires des structures en ligne,
déplacements nommés, pop/replace/try_push, emprunts des cases, tranches,
push_new et compositions générales. Reset n’est pas réintroduit.
Aucun modèle indépendant nouveau ni campagne de mutations/aléatoire dans
ce lot, conformément à la priorité donnée à l’implémentation. Les résultats
natifs et UBSan ne constituent pas une preuve générale de sûreté.

Snapshot : /tmp/crust-before-async-inline-vectors. Patch et empreintes :
validation/async-inline-vectors.patch et async-inline-vectors-changes.json.
Fixture admise et C : validation/async-inline-vectors.crust et .c.
