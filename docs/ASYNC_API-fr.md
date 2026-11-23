[English](ASYNC_API.md)

# API synchrones par défaut et variantes asynchrones explicites

Cette organisation de la STD ne change pas les règles de capture, déplacement,
emprunt, durée de vie des branches ou destruction. `main` reste synchrone.

| API | Synchrone | Asynchrone |
| --- | --- | --- |
| Fichiers | `std::io::File` | `std::io::asyn::File` |
| Flux tamponnés | `std::io::buffered` | `std::io::asyn::buffered` |
| TCP / UDP | `std::net::{tcp, udp}` | `std::net::asyn::{tcp, udp}` |
| Attentes et Timer | `std::time` | `std::time::asyn` |
| Mutex | `std::sync::Mutex` | `std::sync::asyn::Mutex` |
| TLS actuel | `std::net::tls` | Non implémenté |

Les modes et permissions restent dans `std::io`, les adresses dans
`std::net::ipv4`, Duration et Instant dans `std::time`. Les anciens chemins
`std::io::sync`, `std::net::sync` et `std::time::sync` sont supprimés.
`std::sync` regroupe les primitives de synchronisation et `std::sync::asyn` leurs variantes asynchrones. Les opérations asynchrones exigent `.await`.
Les fichiers et délais asynchrones utilisent des workers bloquants ; les
sockets utilisent epoll, kqueue ou IOCP. Les fonctions de configuration et les
accesseurs en mémoire restent synchrones lorsque cela convient.

## Mutex

Chaque variante possède sa valeur `T`. `new(value)` crée sa ressource native.
`lock(&self)` produit une garde ; la variante asynchrone doit être attendue.
`ref()` et `mut_ref()` sur la garde empruntent la valeur. En Corbo, `&mut`
exprime une permission de mutation, sans exiger l'unicité de la référence.
Le mutex doit survivre aux gardes et aux attentes en cours.

Le contrat ordinaire `#(lock: on=self, through_result=true)` maintient la
protection jusqu'à la destruction de la garde. Les noms Mutex n'ont aucun sens
spécial pour le vérificateur. L'implémentation effectue le verrouillage.

La garde synchrone porte `#(thread: transfer=false)` : son déverrouillage appartient
au thread qui l'a acquise. La garde asynchrone peut migrer entre workers.
Son attente utilise une file FIFO et le réveil des tâches, sans boucle active
ni worker bloquant par acquisition. La destruction libère le verrou puis
nettoie les champs. La réentrée avec une garde encore détenue est refusée par
l'analyse des contrats existants.

[Rapport de validation](cycles/SYNC_DEFAULT_MUTEX_CYCLE.md).

Les fonctions brutes de gestion des identifiants natifs restent privées à la
STD. Une implémentation externe d’un type public n’obtient pas l’accès à ses
champs privés.
