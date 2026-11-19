[English](CLOSURES_CYCLE.md)

# Closures réutilisables

Le profil numérique abaisse les closures exercées vers une structure locale
par expression et une méthode appelée par emprunt partagé. La construction
et l'appel utilisent les vérifications ordinaires de l'initialisation, du
transfert, de l'emprunt et du nettoyage. Pour un paramètre
`closure(...) -> R`, le compilateur vérifie la signature et spécialise
la fonction synchrone pour le type concret transmis.

## Exécutions

- Cinq méthodes de test réussies à `-O0` et à `-O2` sous UBSan fatal.
  Elles couvrent six exécutions natives et sept refus statiques par niveau.
  Elles vérifient notamment la copie à la création, deux appels sur une
  même instance, deux spécialisations concrètes, la conservation des
  dépendances d'une référence partagée, le refus d'une cible détruite trop
  tôt et le réemploi du slot après la destruction d'une capture propriétaire.
- La passe à `-O2` avec les régressions numériques, les blocs natifs et les
  contrats de type de fonction compte 31 tests réussis. Une première passe
  avait également découvert les tests historiques de `type feature` par
  l'import de leur classe d'aide. Elle retrouve l'échec déjà consigné dans
  [CORE_ANNOTATIONS_CYCLE.md](CORE_ANNOTATIONS_CYCLE.md) pour
  `type feature Plain { fn a(self); }`.

## Périmètre restant

La représentation actuelle des structures sait stocker les références
aux cellules de pool testées ici. Une référence à un scalaire local utilise
une autre représentation et sa capture reste à raccorder. Les captures
mutables et les valeurs composées par valeur sont également partielles.
Les signatures de fonction avec paramètre closure sont spécialisées à
partir des appels concrets. La vérification indépendante d'une fonction
jamais appelée, la spécialisation récursive, les paramètres closure async
et la coexistence avec les contrats de type annotés restent ouverts.
Ce cycle porte sur des cas ciblés, sans audit indépendant ni campagne de
mutations.
