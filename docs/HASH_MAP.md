[Français](HASH_MAP-fr.md)

# HashMap

The HM1–HM6 rules define the perimeter chosen for the first version.

**HM1 — Keys.** `HashMap<K,V>` accepte `i32`, `i64`, `u8`, `u16`, `u32`,
`u64` and `bool` Each key identifies at most one entry.
equal keys produce the same hash. A collision between separate keys
preserves both entries and the search distinguishes them by equality.

**HM2 — Insertion and replacement.** `insert(&mut self, key: K, value: V)`
renvoie `None` when a new entry is created and `Some(ancienne_valeur)`
when the key already exists. The replacement reuses the location of the entrance.
It remains possible when the area is full. The call moves the connections
to keep the link
The programme calls for `insert(copy(cle), valeur)`. The table
restores the old value by transfer.
If a new entry does not fit in the storage, `insert` adopt the programme
with a diagnosis. In the same case, `try_insert` leaves the table intact and
makes the value entering in `Err`. If successful, it shall cover the same
result`insert` in `Ok`.

**HM3 — Emprunts.** `get(&self, key: &K) -> Option<&V>` borrows the value
stored, even if `V` is `Copy`. `get_mut(&mut self, key: &K) -> Option<&mut V>`
allows to modify it in place. An absent key gives `None`. The reference
The key loan stops after the search.
The loan is on the entire table until the last use of the reference
A shared loan forbids the transfer of the table. A transferable loan
also forbids other readings, even for a different key.

**HM4 — Extraction and destruction.** `remove(&mut self, key: &K) -> Option<V>`
requires exclusive access to the table. It returns `None` for an absent key,
Otherwise it removes the entry and restores its value.
destroys the values still present. An extracted or replaced value remains
under the responsibility of its new recipient.

**HM5 — Stockage.** The table can grow on the data stack within the limit of
The area of the site.
their address during the growth and reorganization of the index.
insertion reuses the freed sites before increasing the area of the
The indexing algorithm is an implementation.

**HM6 — Dependencies.** The table may contain values `A<T>` from
different pools. Each value keeps its original pool and prevents its
destruction as long as it depends on it. The table can also contain `&T`
ou `&mut T`. It keeps the loan of each entry and transmits it with
the value extracted. `V = &mut T`, `get` renvoie un `&&mut T` in `Some`
and `get_mut` un `&mut &mut T`. Change the stored reference replaces the
Dependence on the entrance. Changing its target keeps this dependency.

The [Integration Report](cycles/HASHMAP_LOCK_INTEGRATION_CYCLE.md) described the
transactions carried out from Corbo code and representation limits and
The data are available from the database.
