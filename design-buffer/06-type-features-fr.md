[English](06-type-features.md)

# Brouillon 06 — Type features et résolution statique

Décisions validées dans l’atelier, à intégrer sur demande.

## Déclaration et portée

Une `type feature` est une contrainte structurelle nommée qui déclare
exactement une méthode. Elle s’emploie dans les signatures de fonctions.
Les champs de structures et les collections restent des types concrets
dans cette première version.

```rust
type feature Tracer {
    fn trace(&self);
}

type feature Ajoutable {
    fn ajouter(&mut self, valeur: Int);
}

type feature Fermable {
    fn fermer(-> self);
}
```

Le receveur de la méthode concrète s’écrit selon ME1. Par exemple,
`fn fermer(-> self);` exige une méthode `fn fermer(self: -> Journal)`
sur `Journal`. Son appel consommant conserve la notation de ME4,
`(-> journal).fermer()`.

La déclaration `type feature` remplace les propositions d’annotations
`#(type, ...)` et `#(types, ...)` pour ce concept. Les contrats à
plusieurs méthodes relèvent des futurs traits. Les relations qui
imposent le même type concret à deux arguments sont reportées.

## Résolution et vérification

- Un type satisfait une feature quand il fournit la méthode de signature
  requise. Le compilateur choisit la méthode à la compilation.
- Deux arguments qui portent la même feature peuvent avoir des types
  concrets différents. Le compilateur vérifie et résout chacun séparément.
- Les exigences directes et indirectes doivent être garanties par la
  signature. Le corps peut appeler la méthode déclarée sur la valeur
  contrainte. Il peut aussi passer cette valeur à une fonction dont la
  contrainte est déjà satisfaite par la garantie disponible.
- La feature décrit la signature de la méthode. Les effets, origines
  d’emprunts et dépendances sont déduits de la méthode concrète résolue
  et intégrés au contrat d’appel.
- Une feature peut apparaître dans un type de retour si le compilateur
  peut déterminer le type concret du résultat. Renvoyer un argument
  emprunté conserve son type concret et son emprunt d’origine.

## Exemple admis

```rust
type feature Tracer {
    fn trace(&self);
}

struct Console {
    niveau: Int,
}

struct Journal {
    compteur: Int,
}

impl Console {
    fn trace(self: &Console) {
        print(self.niveau);
    }
}

impl Journal {
    fn trace(self: &Journal) {
        print(self.compteur);
    }
}

fn tracer(tracer: &Tracer) {
    tracer.trace();
}

fn tracer_deux(a: &Tracer, b: &Tracer) {
    tracer(a);
    tracer(b);
}

fn tracer_et_renvoyer(tracer: &Tracer) -> &Tracer {
    tracer.trace();
    return tracer;
}

fn main() {
    let console = Console { niveau: 1 };
    let journal = Journal { compteur: 2 };
    tracer_deux(&console, &journal);

    let resultat = tracer_et_renvoyer(&console);
    print(resultat.niveau);
}
```

`tracer_deux` résout chaque argument vers sa méthode concrète, à
travers le relais `tracer`. `resultat` est un `&Console`.

## Cas refusés

| Cas | Motif |
| --- | --- |
| Déclarer deux méthodes dans `type feature Tracer`. | Une feature contient exactement une méthode. |
| Passer à `tracer` une valeur sans méthode `trace` conforme. | La contrainte exige le mode du receveur et la signature déclarés. |
| Appeler `tracer.flush()` dans un corps qui reçoit seulement `&Tracer`. | La méthode est absente de la garantie disponible. |
| Passer ce même `&Tracer` à une fonction qui exige `flush`. | L’exigence indirecte est absente de la signature. |
| Déclarer un champ `sortie: Tracer` ou `sortie: &Tracer`. | Les features sont réservées aux signatures de fonctions. |

## Directive de région

La notation retenue pour la directive de région est
`#(directive, stack_region_max_size=1M)`. Les espaces autour de `=`
sont facultatifs. Le premier mot après `#(` identifie la catégorie
de l’annotation. Les type features ont leur propre déclaration.

## Règles à compléter lors de l’intégration

- **I5, B4 et B5.** Introduire les contraintes structurelles nommées
  dans les signatures. Préserver le suivi des modes, des effets et des
  provenances au moyen des contrats de méthodes résolues.
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)
- **ME1, ME2 et ME4.** Relier les trois modes de receveur déclarés dans
  une feature aux signatures et aux appels de méthodes concrets.
  [STRUCTURES_METHODS.md](../docs/STRUCTURES_METHODS.md)
- **G6 et P2.** Mettre à jour la syntaxe des directives de région.
  [GROWING_REGIONS.md](../docs/GROWING_REGIONS.md) ·
  [LANGUAGE_RULES.md](../docs/LANGUAGE_RULES.md)

Exemples de conception examinés sur papier.
