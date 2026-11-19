[English](CORE_ANNOTATIONS_CYCLE.md)

# Directives, contrats de type, verrous et vecteurs descendants

Les directives source `#(directive: …)` sont lues par le parseur.
`stack_region_max_size` accepte `K`, `M` et `G` et vérifie la taille avant
conversion. `async_pool_sizes` exige au moins une entrée. La virgule de
l'ancienne syntaxe reste acceptée pour les programmes du prototype.

Le contrat `#(type: T<R> with { … })` lie les noms à la fonction annotée.
Le résolveur vérifie les méthodes utilisées dans le corps, même en l'absence
d'appel. À l'appel, il vérifie les signatures exigées, déduit le même `R`
pour toutes les méthodes et contrôle les alternatives éventuelles. La
spécialisation passe ensuite par le vérificateur ordinaire et la génération C.
Pour une Future issue d'une `async fn`, le résolveur utilise les signatures
`id` et `poll` du runtime intégré. Un auxiliaire peut transférer la tâche à
`runtime::spawn` et retourner un `runtime::Handle<R>`.

Les deux formes de `lock` et la représentation orientée des tranches
descendantes étaient déjà présentes. Le cycle a rejoué leurs tests existants.

## Vérifications exécutées

- **19 tests ciblés réussis** avec `-O2` et UBSan sur le C exécuté.
  Contrats nominaux spécialisés sur `i64` et `bool`, signatures incompatibles,
  alternatives, désaccord entre deux méthodes sur `R` et méthode non déclarée.
  Contrat Future jusqu'au `join()`, avec refus du `drop` prématuré de la cible
  capturée. Directives source et limites des trois unités. Deux formes de
  `lock`, capture et échec de lancement. Ordre et adresses des tranches
  dans les deux sens, y compris une sous-tranche relayée par une tâche.
- **Passe élargie de 88 tests** avec les mêmes options. 86 réussites et deux
  échecs sur des programmes sans nouveau contrat. Le test historique attend
  le refus de `fn a(self);` dans une `type feature` alors que son parseur
  admet déjà ce receveur. Un retour async historique `Handle<Bool>` produit
  un accès à `CrustJoinResult.bool_value` que le C émis ne déclare pas.

Le compilateur vérifie les opérations du corps spécialisé avec ses types
concrets. L'inférence du contrat part d'un paramètre direct de type `T` et
des signatures exigées. La manipulation directe de `Context` et de
`Poll<R>` dans un poller utilisateur reste hors du runtime intégré.
La campagne adversariale et la suite générale restent distinctes de cette
passe.
