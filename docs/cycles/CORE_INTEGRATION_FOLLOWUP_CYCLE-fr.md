[English](CORE_INTEGRATION_FOLLOWUP_CYCLE.md)

# Intégration des closures, des branches et des corrections du noyau

## Corrections du compilateur

- Les projections de tableaux retournées par une tâche conservent les
  coordonnées numériques et inconnues. Le compilateur traite séparément
  les chemins de champs nommés. Les témoins couvrent une projection constante
  via `join()`, une projection dynamique via `.await` et un échec de
  lancement injecté suivi d'un nouvel accès au tableau.
- `match h.await` lit le champ booléen renseigné par la récupération du
  résultat. Un `if` combinant un booléen attendu et un booléen local conserve
  le type dans les branches exercées.
- Le typage refuse l'annotation scalaire `i32` pour une allocation
  `A<i32>`. Une écriture indexée dans un tableau emprunté transmet le type
  de l'élément au littéral avant l'abaissement async.

## Closures et branches

Une closure peut recevoir une structure locale par `move`. L'appel partagé
projette la capture en lecture et sa destruction nettoie la structure
transférée une seule fois. Les captures de références vers des scalaires
locaux et les autres cas ouverts dans [le cycle des closures](CLOSURES_CYCLE.md)
restent à raccorder.

Les wrappers synchrones `#(branch)` et
`#(branch: join=result.join())` sont vérifiés lorsqu'ils retournent un
lancement direct, éventuellement via une liaison locale immédiate. La
vérification d'un corps général et la propagation de la preuve d'abandon
à travers un handle public restent ouvertes.

Dans le profil numérique, le compilateur autorise l'abandon d'un handle
concret quand la signature et les dépendances suivies établissent un
lancement à captures scalaires et résultat scalaire ou vide. Le runtime
réutilise sa file de tâches abandonnées. Il récupère les tâches terminées
lors de l'abandon, d'une allocation de tâche ultérieure ou de la fermeture
du contexte. La récupération systématique à la terminaison et le calcul
de capacité en présence d'abandons successifs restent à compléter.
`spawn_blocking` est réservé au contexte async dans le profil cible et
son résultat local accepte une annotation `AsyncHandle<R>` vérifiée.
La distinction des handles à travers les signatures reste ouverte.

## Exécutions

- Les 13 tests de `test_core_pending` et `test_closures` passent sous
  UBSan à `-O0` et `-O2`.
- Les 13 méthodes historiques de projection recensées dans le tri passent
  sous UBSan à `-O2`.
- La passe élargie de 40 tests à `-O2` passe, notamment la matrice des
  résultats de handles publics, les anciens cas booléens, les obligations
  d'attente du profil historique et les régressions numériques. Cette passe
  précède les derniers ajouts de tests ciblés.

Ces passes ciblent les écarts recensés. La suite générale et l'audit
indépendant restent à rejouer.
