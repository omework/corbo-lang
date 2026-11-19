[English](OWNED_RESULTS_CYCLE.md)

# Résultats propriétaires — cycle du 7 novembre 2026

## Périmètre et statut

Intégration partielle du brouillon 01, règles U1/L6/F2/H1/VE3/VE4.
Les règles normatives sont mises à jour dans LANGUAGE_RULES.md et
FOUNDATIONS_AND_VECTORS.md. Le lot et l'objectif global restent ouverts.

Le contrôle porte sur le type : même un `pop` statiquement vide ne permet
pas `Some(_)`, ni une liaison propriétaire inutilisée. Une variante entière
masquée par `_` ne peut pas dissimuler une allocation. Le succès unité de
`try_push` et les détails d'erreur sans allocation peuvent être ignorés.
Les champs propriétaires d'enums consommés suivent le même contrôle, même
si la variante concrète est connue. Une lecture conditionnelle suffit ;
le nettoyage de portée reste exécuté si cette lecture n'a pas lieu.

`drop(-> v.pop())` et `drop(-> v.try_push(-> entrant))` sont abaissés vers
une réception temporaire suivie d'une destruction. Les analyses de contraintes,
d'effets et de résultats reconnaissent ces opérations. Le C détruit seulement
le contenu possédé de la variante réelle, avant l'instruction suivante.
Le test d'emprunt vérifie l'appel à travers deux fonctions et l'interdiction
d'utiliser un alias après destruction. Les adresses sont comparées lors du
réemploi d'un pool d'un slot.

## Défauts et adaptations

- Le contrôle après évaluation ne suffisait pas : une branche `Some` pouvait
  être éliminée sur un vecteur vide. Le contrôle du motif précède désormais
  cette évaluation.
- Le chemin async acceptait `Ok(_)` et `Ok(inutilise)` sur un résultat de
  handle possédant une allocation. Il contrôle désormais les motifs et
  usages explicites ; une liaison inutilisée de résultat d'attente est refusée.
- Ce nouveau contrôle a initialement rejeté un export valide en fin de bloc
  async : le dernier `<- r` était retiré du corps avant le contrôle. Le nom
  exporté est maintenant transmis au contrôle d'usage.
- Plusieurs anciens tests autorisaient explicitement l'abandon propriétaire.
  Ils utilisent maintenant des liaisons nommées, des lectures ou `drop`.
  Les tests d'interdiction de copie et de types incompatibles utilisent leur
  liaison pour ne pas masquer le diagnostic visé par U1.
- Une trace change intentionnellement : lorsque les deux champs d'un enum
  sont extraits, son conteneur vide est détruit avant le corps du bras ; le
  `drop` explicite du second champ arrive ensuite. L'ancien motif `_`
  détruisait ce champ pendant le démantèlement du conteneur. La nouvelle
  attente conserve une trace exacte et la vérification du réemploi.
- Les fixtures de nouveaux tests ont également été corrigées : construction
  d'un champ avec `<-`, et comparaison d'un `&A<Int>` via `vequals` plutôt
  qu'une tentative de lecture comme un `&Int`.

## Preuves exécutées

`tests/test_owned_results.py` : neuf méthodes, huit programmes natifs admis
et 58 configurations refusées par passage. Les cas combinent présence/absence,
match immédiat/différé, motifs, appels, emprunts, destruction, capacité,
provenance, réemploi et attente async.

Exécution à `-O0` et `-O2`, clang C11, UBSan avec
`-fno-sanitize-recover=all` : neuf méthodes réussies à chaque niveau,
respectivement 4,963 s et 4,025 s au passage final.
Journal : `/tmp/crust-owned-results-optimizations-final.log`.
Ce passage inclut aussi le cas admis `Some(_)` sur un élément Copy.
Commande de reproduction du passage standard :

```sh
PYTHONPATH=.:tests python3 -m unittest test_owned_results -v
```

Le script `/tmp/crust_owned_optimizations.py` remplace uniquement le niveau
`-O2` des commandes de compilation par le niveau choisi ; il conserve le
sanitizer et ses erreurs fatales.

Régression initiale : 140 méthodes de FoundationTests dont le nom contient
`handle`, `consum` ou `owned_field`, 80,128 s, cinq échecs et 25 erreurs.
Journal : `/tmp/crust-owned-result-initial-regression.log`.
Après première migration : 147 méthodes (les 140 et les sept nouveaux tests
alors présents), 95,493 s, deux échecs et quatre erreurs. Les causes ont été
corrigées : un motif restant, l'ordre du transfert d'entrée de scope, un
motif d'enum imbriqué et la trace de démantèlement décrite ci-dessus.
Les quatre méthodes concernées passent ensuite en 4,274 s
(`/tmp/crust-owned-migration-corrected.log`).

Première régression async : 26 méthodes dont le nom contient `owned`,
64,909 s, deux échecs et cinq erreurs. Elle a détecté les anciennes attentes
d'abandon, des diagnostics masqués et le défaut d'export de bloc ci-dessus.
Journal : `/tmp/crust-owned-async-regression.log`.
Relances finales après corrections :

- 140 méthodes synchrones réussies en 115,324 s :
  `/tmp/crust-owned-foundation-final.log`.
- 26 méthodes async réussies en 68,306 s :
  `/tmp/crust-owned-async-final.log`.
- Compilation Python des six modules modifiés et des trois modules de tests :
  réussie (`python3 -m py_compile ...`).

Les sélections sont reproductibles avec `unittest.defaultTestLoader` :
FoundationTests conserve les noms contenant `handle`, `consum` ou `owned_field` ;
AsyncRuntimeTests conserve les noms contenant `owned`. Les sous-cas des tests
historiques ne sont pas confondus avec leur nombre de méthodes.

## Mutations

Trois copies temporaires du compilateur, tests et attentes inchangés :

| Faute injectée | Observation | Classification |
| --- | --- | --- |
| Suppression du contrôle du type de payload avant évaluation | 18 sous-cas invalides acceptés | Détectée |
| Suppression du contrôle de motif propriétaire dans le bras async | Trois motifs invalides acceptés | Détectée |
| Omission de `cell_drop` dans le nettoyage conditionnel | Le programme valide ne peut plus réallouer son unique slot : `pool capacity exceeded` | Détectée |

Journal : `/tmp/crust-owned-results-mutations.log` ; script reproductible
`/tmp/crust_owned_mutations.py`. Les répertoires des mutants sont inscrits
dans le journal. Ce petit échantillon ne donne pas un taux global de détection.

## Limites et travail restant

- U1 n'est pas encore généralisé à toutes les liaisons propriétaires.
  Contre-exemples acceptés à la fin de cette première étape, puis corrigés dans
  [U1_RECEIPTS_CYCLE.md](U1_RECEIPTS_CYCLE.md) :

  ```rust
  let mut p = pool<Int>(1);
  let unused = p.new(1);
  ```

  ```rust
  async fn f(n: -> Int) -> <- Int { return <- n; }
  async fn g(n: -> Int) { let unused = f(-> n).await; }
  ```

  Ces écarts ont été corrigés au cycle suivant ; ils ne constituent pas une
  exception normative. Les wrappers déplacés et les résultats async imbriqués
  nécessitent aussi un audit systématique de chaque chemin de réception.
- Pas de nouvelle preuve formelle, de campagne ASan/TSan ni de modèle général
  indépendant dans cette étape. Les oracles des nouveaux tests sont les
  résultats, adresses, événements de destruction et limites de pool spécifiés
  directement ; ils ne déduisent pas l'attendu du C généré.
- Les régressions historiques de reset utilisent explicitement le profil
  `allow_legacy_reset=True`. Elles vérifient les interactions historiques,
  pas la disponibilité de cette API dans le prototype public.
- Les validations sont ciblées. La suite globale de Crust et les autres
  lots (stockage complet, type features, dernier runtime/scheduler/Select/
  mutex) ne sont pas déclarés achevés par ce cycle.
