[English](STRUCTURE_VIEW_RUNTIME_CYCLE.md)

# Emprunts de sous-structures — représentation interne

## État du chantier

Étape d'implémentation en cours de ST7, sans modification normative.
Ce lot prépare le stockage et les métadonnées ; il ne rend pas encore la
syntaxe d'emprunt de sous-structure utilisable dans Crust.

`validation/open-inline-structure-borrow.crust` décrit le cas attendu valide :
emprunter `segment.debut`, le transmettre à `modifier(&mut Point)` et accéder
au champ disjoint `segment.fin.x`. Les deux entrées du compilateur le refusent
encore avec « champ inconnu 'debut' dans Segment » ; observation conservée dans
`validation/structure-view-source-gap.log`. Ce refus est un écart d'implémentation,
pas une preuve de respect d'une règle de refus.

## Représentation ajoutée

Le compilateur conserve désormais `inline_structures` en plus de son layout
aplati. Chaque entrée retient le chemin, le type nominal et la plage de champs
terminaux. Les offsets restent exprimés en indices jusqu'au backend C : les
tailles de pointeurs de la machine hôte Python ne sont pas supposées.

`CrustStructureView` est un descriptif transmis par valeur : racine `Cell *`,
décalage, taille et layout. Une projection supplémentaire compose les décalages
sur la même racine. Un retour ne conserve ainsi aucun pointeur vers une variable
descriptive locale du callee. Il n'alloue ni slot ni objet supplémentaire et
n'offre aucune opération de destruction indépendante.

Les primitives de lecture/écriture utilisent les octets de la racine existante,
avec `memcpy` pour conserver le traitement des champs potentiellement non alignés.
Les limites de la vue sont contrôlées avant l'accès. Les permissions partagé/mutable
et la durée de vie doivent encore être imposées par le vérificateur source.
La possibilité de copier le descriptif en C ne constitue pas une autorisation
de copier un emprunt mutable dans le langage.

## Vérifications exécutées

Cinq méthodes dans `tests/test_structure_view_runtime.py` : une vérification des
métadonnées du compilateur et six exécutions C. Trois exécutions réussissent ;
trois déclenchent le diagnostic de limites attendu.

- Chemins nominaux imbriqués, plages et layout aplati cohérents.
- Retour du descriptif à travers deux fonctions C, modification dans le slot
  d'origine, champ voisin inchangé, une seule allocation vivante puis réemploi.
- Référence partagée stockée : cible identique et non détruite avec le porteur.
- Vue conservée dans un état de tâche, suspension, reprise sur un autre pthread,
  extraction puis destruction explicite de la racine après attente.
- Offset hors allocation, projection hors parent et champ hors vue diagnostiqués
  avant l'accès.

| Passage | Résultat | Journal dans `validation/` |
| --- | --- | --- |
| Ciblé initial O0 | 5 méthodes, 1 échec de sonde, 1,925 s, code 1 | `structure-view-runtime-o0.log` |
| Ciblé final O0 | 5 méthodes, 2,096 s, code 0 | `structure-view-runtime-o0-final.log` |
| Régression finale O2 | 34 méthodes, 19,798 s, code 0 | `structure-view-runtime-regression-o2.log` |

Clang C11/pthread, avertissements comme erreurs, UBSan fatal ; aucun test sauté.
La première sonde ajoutait les définitions de valeurs communes une seconde fois.
Elle utilise maintenant `TASK_RUNTIME_BODY` avec les types déjà émis. Aucun
comportement attendu n'a été affaibli. Les 34 méthodes comprennent les tests
des constructeurs imbriqués, copies async et pools de structures async.

## Suite requise et limites

Restent à raccorder, avant de déclarer cette fonctionnalité implémentée :

1. Les expressions d'emprunt et le typage des sous-structures.
2. La réservation d'un préfixe de chemin et ses réemprunts jusqu'au dernier usage.
3. Les paramètres, retours et contrats, y compris les références reçues après appel.
4. Les captures/retours async et les références stockées dans d'autres valeurs.
5. Les tests source admis/refusés concernant la destruction et les transferts.

Ces tests d'ABI ne prouvent ni ces obligations statiques ni la sûreté générale.
Le test multithread manipule directement l'ABI interne ; il ne démontre pas
encore qu'un programme Crust utilisant une vue de sous-structure compile.
Pas de nouvelle campagne adversariale, de mutations ou de modèle indépendant.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest -v test_structure_view_runtime
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 python3 -m unittest -v test_structure_view_runtime test_inline_structure_construction test_async_direct_copy test_async_struct_pools
```

Snapshot initial : `/tmp/crust-before-inline-structure-views/`.
Patches dans `validation/structure-view-runtime-{crust,structure_views}.py.patch`.
