[English](ASYNC_API.md)

# I/O async par défaut et API bloquantes explicites

Cette convention organise les API de la STD ; elle ne modifie ni la grammaire,
ni les règles de capture, de move, d’emprunt ou de nettoyage. `main` reste
synchrone et `.await` reste explicite dans un corps async.

| API | Async par défaut | Bloquant explicite |
| --- | --- | --- |
| Fichiers | `std::io::File` | `std::io::sync::File` |
| Flux tamponnés | `std::io::buffered::{BufReader, BufWriter}` | `std::io::sync::buffered::{BufReader, BufWriter}` |
| TCP | `std::net::tcp` | `std::net::sync::tcp` |
| UDP | `std::net::udp` | `std::net::sync::udp` |
| Sleep et Timer | `std::time::{sleep, Timer}` | `std::time::sync::{sleep, Timer}` |
| Transport TLS actuel | Non implémenté | `std::net::sync::tls` |

Les types communs restent dans leurs packages : FileMode, FilePerm, FileStats et
SeekFrom dans `std::io` ; SocketError/Datagram dans `std::net`, les adresses dans
`std::net::ipv4` ; Duration/Instant/Error dans `std::time`. Les enveloppes d’erreur
File et BufferedError restent propres à chaque variante. `Instant::remaining()`
mesure la durée restante jusqu’à une échéance sans accéder aux champs privés
d’un autre module.

Les fichiers et timers async utilisent les workers bloquants existants ; les
sockets conservent epoll/kqueue/IOCP. Bind, UDP connect, les accesseurs addr/peer
et les constructeurs de timers gardent leur signature synchrone actuelle. Le
choix d’un package ne rend pas tous ses calculs asynchrones.

Aucune conversion implicite sync/async. Parseurs, encodage, cryptographie et
collections restent des calculs synchrones. Le TLS existant est déplacé intact
sous sync ; aucun transport TLS async n’est ajouté. HTTP garde son contrat de
lecture actuel. Les anciens packages publics `asyn` sont supprimés ; le module
interne `std::sys::net::asyn` reste un détail d’implémentation. Le compilateur
charge ses fichiers avec `std::io::sync::File`.

Le nettoyage en fin de bloc est automatique. `drop(value)` reste pertinent pour
une libération anticipée volontaire, par exemple fermer un fichier avant sa
suppression sous Windows. Il n’est pas nécessaire dans chaque bras d’erreur.

[Résultats d’intégration](cycles/ASYNC_DEFAULT_API_CYCLE.md).
