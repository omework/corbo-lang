[English](DIRECTIVES_CYCLE.md)

# Cycle — Directives catégorisées (brouillon 06)

## Décision appliquée

La directive de région s’écrit désormais
`#(directive, stack_region_max_size=1M)`. La catégorie et sa virgule sont
obligatoires ; les espaces autour de `=` sont facultatifs. Le parseur ne
conserve pas un alias silencieux pour l’ancienne forme sans catégorie.
Les catégories `type` et `types` ne remplacent pas `type feature`.

G6, P2 et les exemples normatifs de chaînes ont été actualisés avant la
validation. Les exemples historiques des rapports et les brouillons de
conception ne sont pas réécrits. Les programmes de tests actifs utilisent
la syntaxe validée ; l’ancienne forme subsiste comme cas refusé explicite.

## Invariants et interactions examinés

Cette modification ne change pas le placement, la taille ou la durée de vie
d’une région. Le parseur transmet la même valeur entière aux blocs et aux
expressions de bloc. Les contrôles portent sur l’héritage lexical, la
surcharge dans un enfant, la restauration à sa sortie et l’absence
d’héritage dynamique dans une fonction appelée. Les cas natifs exercent
les String et Vector, les transferts parent/enfant, les branches de match,
la réservation avant construction, les adresses conservées, les limites
après transfert, les slots réutilisés et le nettoyage des éléments possédés.

Le modèle numérique des tests emploie des constantes décimales indépendantes
du parseur : 1048576 et 1073741824. Les multiples binaires sont toujours une
convention du prototype ; ce cycle ne tranche pas la question normative des
unités. Des nombres à la limite et immédiatement au-delà vérifient la borne
de représentation sans tenter de réserver réellement des exaoctets.

## Preuves exécutées

- `PYTHONPATH=tests:. python3 -m unittest test_growth_annotations -v` :
  4 méthodes réussies ; 13 programmes admis par compilation et
  26 configurations refusées. Les refus couvrent catégorie, séparateur,
  paramètre inconnu/dupliqué, emplacement, unité, zéro, négatif et débordement.
- `/tmp/crust_directive_cycle.py -O0` : 20 méthodes réussies en 15,231 s.
- `/tmp/crust_directive_cycle.py -O2` : les mêmes 20 méthodes réussies en
  16,575 s. Le script sélectionne les méthodes contenant la directive dans
  `test_foundation_rules` et `test_owned_results`, plus `test_growth_annotations`.
  Il ne change que le niveau d’optimisation dans les commandes natives.
  Le C est compilé avec `-fsanitize=undefined -fno-sanitize-recover=all`.
- Journaux : `/tmp/crust-directive-O0.log` et `/tmp/crust-directive-O2.log`.
- Compilation Python des fichiers modifiés réussie.

### Mutations

Trois mutations de `crust.py` ont été exécutées dans des copies temporaires,
avec les tests originaux de `test_growth_annotations` :

1. Accepter l’absence de catégorie : détectée par un programme historique
   accepté à tort.
2. Accepter l’absence de virgule : détectée par un programme mal formé
   accepté à tort.
3. Interpréter M/G avec des facteurs décimaux : détectée par les limites
   observées et les bornes du modèle numérique.

Toutes provoquent des assertions de test, sans erreur de chargement ou de
syntaxe Python. Script : `/tmp/crust_directive_mutations.py` ; journal :
`/tmp/crust-directive-mutations.log`. Ces trois fautes ciblées ne mesurent
pas une couverture générale du compilateur.

## Régression et migration des anciennes fixtures

La régression élargie a exposé des fixtures antérieures à U1 qui créaient
un propriétaire inutilisé, parfois écrasé ou détruit par un reset sans
usage explicite. Le compilateur refuse désormais ces programmes avant le
comportement que le test cherchait à exercer. Les fixtures ont été adaptées
par des lectures `print` avant le nettoyage ou le remplacement, avec sorties
attendues explicites. Les assertions de destruction et de réemploi sont
conservées. Les cas négatifs utilisent les autres propriétaires pour isoler
le diagnostic de l’ancien accès invalide ou du type de pool incompatible.
Le profil historique `allow_legacy_reset` reste explicite dans ces tests.

Exécution initiale :
`PYTHONPATH=tests:. python3 -m unittest test_crust test_arguments test_if_expressions test_growth_runtime test_owner_usage -v` :
215 méthodes en 116,554 s, avec 4 échecs d’assertion et 27 erreurs (plusieurs
sous-cas par méthode) dus aux fixtures U1 décrites ci-dessus. Journal conservé :
`/tmp/crust-directive-regression.log`.

Après correction des fixtures :
`CRUST_SANITIZE=undefined PYTHONPATH=tests:. python3 -m unittest test_crust test_arguments test_if_expressions -v` :
181 méthodes réussies en 80,164 s, UBSan fatal activé pour les programmes C.
Journal : `/tmp/crust-directive-fixtures-final.log`.
Les 22 méthodes de `test_growth_runtime` et les 12 de `test_owner_usage`
avaient déjà toutes réussi dans l’exécution initiale ; leur code et le
compilateur n’ont pas changé entre ces deux exécutions. Le runtime de croissance
est exercé à O0/O2 avec UBSan fatal par son helper natif ; les cas U1 utilisent
le helper O2/UBSan. Le modèle U1 indépendant à 64 configurations et les modèles
de croissance/slots ont été réexécutés par ces modules.
Ainsi les 215 méthodes de régression ont une preuve de réussite sur l’état
final, répartie entre ces deux journaux ; il ne s’agit pas d’un unique passage
global de toutes les suites du dépôt. Les nombres de méthodes ne sont pas des
nombres de programmes : certains tests génèrent plusieurs configurations.

## Limites et suite

Ce cycle ne termine pas le brouillon 06. Le programme
`type feature Tracer { fn trace(&self); } fn main() {}` reste refusé au
parseur (`attendu '=', reçu 'feature'`). Déclaration, contraintes structurelles,
résolution statique et contrats de méthodes résolues restent à implémenter.

Un bloc annoté dans une fonction async reste aussi refusé :

```rust
async fn f() -> Int {
    #(directive, stack_region_max_size=1M) { yield; }
    return 1;
}
fn main() { let t = f(); drop(-> t); }
```

Diagnostic observé : `annotation de région non prise en charge dans ce bloc
async`. Le support de la directive dans le parseur n’est donc pas un support
général de ses effets en async. Ce point reste ouvert avec le lot async.
Aucune preuve formelle, aucun nouveau passage ASan/TSan et aucune exploration
exhaustive des compositions de règles ne sont revendiqués. Le chantier global
reste actif, avec les écarts de stockage et les décisions async encore ouverts.


Complément ultérieur : [TYPE_FEATURES_CYCLE.md](TYPE_FEATURES_CYCLE.md) intègre
la déclaration et une première résolution statique des features. Le refus
syntaxique de `type feature` rapporté ci-dessus décrit donc l’état historique
du cycle directives ; il n’est plus un écart actuel. Le catalogue builtin et
les interactions détaillées dans le nouveau rapport restent ouverts.
