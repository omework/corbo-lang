[English](PUBLIC_HANDLE_TYPES_CYCLE.md)

# Type public des handles — annotations de liaisons

## Règle et périmètre

Le brouillon 04 désigne le type public d'une tâche lancée par
`runtime::Handle<T>`, où T est son résultat, indépendamment du type de frame.
Cette étape rend ce type utilisable comme annotation d'une liaison synchrone
ou async. Elle ne termine pas les contrats génériques de paramètres et retours.
Aucune règle normative n'est changée.

Le parseur accepte le nom qualifié et sa charge, y compris les références,
tableaux, allocations et résultats imbriqués. Le vérificateur compare la
charge au résultat déclaré de la tâche. La représentation interne conserve
encore le type concret de frame et ses dépendances : l'annotation ne modifie
ni ses sources, ni ses emprunts, ni son obligation d'attente.

Les captures ne se déduisent pas de T. Un `Handle<Int>` peut encore porter un
emprunt mutable jusqu'à son attente ; `Int` ne décrit que le résultat final.
`Handle<&mut Int>` conserve les protections du résultat après l'attente et
`Handle<A<Int>>` conserve le pool de l'allocation rendue. L'enveloppe du résultat
de lancement reste distincte du résultat métier porté par T.

Exemple désormais exécutable :

```rust
async fn calcul() -> Int {
    yield;
    return 7;
}

fn main() {
    let execution: runtime::Handle<Int> = runtime::spawn(-> calcul());
    match execution.join() {
        Ok(valeur) => { print(valeur); },
        Err(_) => { print(99); }
    }
}
```

## Interactions et défaut corrigé pendant l'intégration

Les annotations s'appliquent aussi aux déplacements de handles, sorties de
blocs, if et boucles, ainsi qu'à spawn_blocking et runtime::thread.
Le premier passage acceptait les liaisons directes mais refusait les trois
formes de transfert calculé dans un corps async : un second contrôle du
receveur ne connaissait pas les handles. Ce contrôle compare désormais lui
aussi le type public, sans contourner le nettoyage ou les transferts.
Reproduction conservée : `validation/public-handle-types-control-o2.log`.

Des fixtures initiales ne respectaient pas les règles existantes : Int as u8
au lieu d'une conversion vérifiée, tableau retourné sans flèche, motif
`Ok(mut view)` absent de la grammaire et print d'un u8 sans conversion explicite.
Elles ont été corrigées ; aucun changement normatif n'en découle. Les journaux
`…-initial-o2.log` et `…-targeted-o2.log` conservent ces échecs.

## Validation

La suite `tests/test_public_handle_types.py` comprend :

- Une matrice de six types (Int, Bool, u8, Void, &str, tableau fixe) dans les
  deux contextes sync/async, avec annotations exactes et voisines incompatibles.
- Deux frames différentes produisant Int, renommage explicite, consommation
  unique et refus de l'abandon de l'attente.
- Captures mutables avec résultat scalaire ou emprunté : accès et drop trop
  tôt refusés, accès après attente permis.
- Résultat alloué : destruction unique, réemploi du pool après attente,
  allocation concurrente dans le pool réservé refusée.
- Six formes de lancement/transfert dans les deux contextes, avec type exact
  et incorrect.
- Résultat métier Result imbriqué, distinct de l'erreur de lancement externe.

Clang C11, pthread, avertissements fatals, UBSan fatal, O0 et O2. Les journaux
finaux sont `validation/public-handle-types-complete-o0.log` et
`validation/public-handle-types-complete-o2.log`.
Les sept méthodes passent : 32,507 s à O0 et 32,800 s à O2. Elles exercent
29 compilations/exécutions C et 35 variantes refusées aux deux entrées
check/compile, soit 70 contrôles de refus par passage complet.
Une régression voisine de 50 méthodes passe en 85,552 s à O2
(`validation/public-handle-types-regression-o2.log`) : obligations d'attente,
contrats mixtes, résultats et pools injectés. Elle a été lancée avant les
derniers compléments du test de contrôle de flux et leurs corrections, couverts
par les passages ciblés finaux.

Trois mutations détectées : omission du contrôle sync, omission des contrôles
async et effacement des dépendances d'une capture lors de l'annotation.
Journal : `validation/public-handle-types-final-mutations-o2.log`.
La première sélection de la dernière mutation échouait sur un résultat
emprunté avant d'atteindre l'accès interdit : classée inconclusive dans le
journal initial. Le test ajouté avec résultat scalaire isole la protection de
la capture et détecte l'accès interdit accepté à tort, aux deux entrées.
Les tests ne sont pas affaiblis pour laisser passer la mutation.

## Écart ouvert et suite de l'intégration

Mise à jour : l'écart scalaire ci-dessous est maintenant traité par le
[cycle des contrats publics](PUBLIC_HANDLE_CONTRACTS_CYCLE.md), également
étendu aux tableaux fixes Int/u8. Le diagnostic conservé décrit l'état à la
fin du présent cycle d'annotations, pas l'état actuel de ces signatures.

`validation/open-public-handle.crust` exige deux fonctions async différentes
produisant Int et un auxiliaire commun qui reçoit `runtime::Handle<Int>`.
Le parseur reconnaît maintenant ce type, mais les deux entrées refusent encore
`type de paramètre inconnu 'runtime::Handle<Int>'`
(`validation/open-public-handle-after-parser.log`). Les signatures historiques
`Execution<fonction>` ne satisfont pas cette règle générale.

Il reste à séparer dans les contrats le type du résultat, les captures actives
avant attente et les provenances conservées par le résultat après attente.
Les signatures génériques, les jonctions de handles issus de fonctions
différentes et leurs résultats empruntés doivent suivre cette séparation.
Leur refus actuel n'est pas une nouvelle restriction normative.

Pas de preuve générale de sûreté, d'ASan/TSan supplémentaire ou de vérification
de tous les types de résultats. Le lot public Handle et l'objectif global
restent ouverts.
