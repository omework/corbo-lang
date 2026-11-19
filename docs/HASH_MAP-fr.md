[English](HASH_MAP.md)

# HashMap

Les règles HM1–HM6 définissent le périmètre retenu pour la première version.

**HM1 — Clés.** `HashMap<K,V>` accepte `i32`, `i64`, `u8`, `u16`, `u32`,
`u64` et `bool` comme clés. Chaque clé identifie au plus une entrée. Deux
clés égales produisent le même hash. Une collision entre clés distinctes
préserve les deux entrées et la recherche les distingue par égalité.

**HM2 — Insertion et remplacement.** `insert(&mut self, key: K, value: V)`
renvoie `None` quand une nouvelle entrée est créée et `Some(ancienne_valeur)`
quand la clé existe déjà. Le remplacement réutilise l'emplacement de l'entrée.
Il reste possible quand la région est pleine. L'appel déplace les liaisons
passées par valeur, y compris celle de la clé. Pour conserver la liaison
de clé, le programme appelle `insert(copy(cle), valeur)`. La table
restitue l'ancienne valeur par transfert.
Si une nouvelle entrée ne tient pas dans le stockage, `insert` arrête le programme
avec un diagnostic. Dans le même cas, `try_insert` laisse la table intacte et
rend la valeur entrante dans `Err`. En cas de succès, il enveloppe le même
résultat qu'`insert` dans `Ok`.

**HM3 — Emprunts.** `get(&self, key: &K) -> Option<&V>` emprunte la valeur
stockée, même si `V` est `Copy`. `get_mut(&mut self, key: &K) -> Option<&mut V>`
permet de la modifier en place. Une clé absente donne `None`. La référence
renvoyée dépend de la table. L'emprunt de la clé s'arrête après la recherche.
Le prêt porte sur la table entière jusqu'au dernier usage de la référence
renvoyée. Un prêt partagé interdit les mutations de la table. Un prêt mutable
interdit aussi les autres lectures, même pour une clé différente.

**HM4 — Extraction et destruction.** `remove(&mut self, key: &K) -> Option<V>`
exige un accès exclusif à la table. Il renvoie `None` pour une clé absente,
sinon il retire l'entrée et restitue sa valeur. La destruction de la table
détruit les valeurs encore présentes. Une valeur extraite ou remplacée reste
sous la responsabilité de son nouveau receveur.

**HM5 — Stockage.** La table peut grandir sur la data stack dans la limite de
sa région. Elle gère son stockage interne. Les entrées encore présentes gardent
leur adresse pendant la croissance et la réorganisation de l'index. Une
insertion réutilise les emplacements libérés avant de faire grandir la zone des
entrées. L'algorithme d'indexation relève de l'implémentation.

**HM6 — Dépendances.** La table peut contenir des valeurs `A<T>` issues de
différents pools. Chaque valeur garde son pool d'origine et empêche sa
destruction tant qu'elle en dépend. La table peut également contenir `&T`
ou `&mut T`. Elle conserve l'emprunt de chaque entrée et le transmet avec
la valeur extraite. Pour `V = &mut T`, `get` renvoie un `&&mut T` dans `Some`
et `get_mut` un `&mut &mut T`. Modifier la référence stockée remplace la
dépendance de l'entrée. Modifier sa cible conserve cette dépendance.

Le [rapport d'intégration](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) décrit les
opérations exercées depuis le code Corbo et les limites de représentation et
de propagation des dépendances du compilateur.
