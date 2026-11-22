# Canaux bornés

`std::sync::channel::Channel<T>` bloque le thread natif pendant une attente.
`std::sync::asyn::channel::Channel<T>` suspend une Future. Les deux proposent
`new(capacity)`, `send(value)`, `recv()` et `close()`. Dans la variante async,
`send` et `recv` s’attendent avec `.await` ; `close()` reste synchrone.

La capacité est strictement positive et limite le nombre de valeurs en file.
Le stockage utilise une région dédiée, avec la limite de taille de région active,
et reste attaché au canal après un move. Aucun agrandissement illimité ni
allocateur général de secours n’est ajouté.

Un envoi réussi transfère la valeur au canal ; une réception la transfère à
l’appelant, dans l’ordre FIFO. Un échec renvoie `SendError.Closed { value }`.
Les primitives gardent leur sémantique habituelle de copie. `close()` est
idempotent et réveille les deux côtés. Les valeurs en file restent recevables,
puis `recv()` retourne `None`. La fermeture n’est pas déduite d’un compteur
d’extrémités : le producteur doit fermer explicitement pour terminer une boucle
qui attend `None`.

La destruction de fin de scope ferme le canal, détruit chaque valeur restante
une seule fois et libère la région. Le canal doit survivre à ses utilisateurs
empruntés et aux opérations async en cours, selon les règles existantes.

## Types admis

L’API vérifiée admet actuellement les primitives et les structures/enums de
taille fixe autonomes, y compris avec destructeur utilisateur. Une restriction
`#(thread: transfer=false)` se propage aux champs possédés et interdit le type
comme charge de canal.

Les charges empruntées ou dépendantes de pools, régions ou tâches externes
restent refusées : le compilateur ne doit pas perdre leur provenance dans la
file opaque. C’est une limite d’intégration documentée, pas une nouvelle règle
de durée de vie.

## Attentes

Une attente async conserve son inscription dans l’en-tête stable de sa Future.
Le contrôle de disponibilité et l’inscription utilisent le même verrou et un
compteur de changement pour éviter les réveils perdus. Le réveil sélectionne
une inscription FIFO, sans exécuter le poll sous verrou. La destruction d’une
Future retire son inscription avant de libérer sa mémoire et transmet un réveil
sélectionné si nécessaire. Les attentes synchrones utilisent une condition
native. Le runtime Corbo et la référence C suivent les mêmes transitions.

[Exemple complet](../examples/features/channels/src/main.crb) ·
[Documentation détaillée en anglais](CHANNELS.md) ·
[Validation](cycles/CHANNELS_CYCLE.md).
