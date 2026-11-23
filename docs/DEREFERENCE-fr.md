# Déréférencement et méthodes de référence

[English](DEREFERENCE.md)

Les deux variantes de `MutexGuard` remplacent `get()` et `get_mut()` par
`ref(&self) -> &T` et `mut_ref(&mut self) -> &mut T`. Elles empruntent la valeur
protégée. La référence reste liée à la garde et à son propriétaire protégé.
`let mut guard` autorise la mutation ; le mutex fournit la synchronisation.

Pour `A<T>`, `allocation.ref()` équivaut à `&*allocation`, et
`allocation.mut_ref()` à `&mut *allocation`. Pour emprunter le handle lui-même,
écrire `&allocation` ou `&mut allocation`.

Les méthodes d’instance déclarées ont priorité sur les raccourcis universels.
Sans méthode déclarée, `value.ref()` reste `&value`, et `value.mut_ref()` reste
`&mut value`. Ces raccourcis ne rendent pas un objet déréférençable.

Le déréférencement natif de `&T`, `&mut T` et `A<T>` reste inchangé.
Pour un objet utilisateur, `*` appelle statiquement la méthode déclarée `ref()`
en lecture ou pour un emprunt partagé, et `mut_ref()` en écriture, pour un
emprunt mutable ou un appel de méthode à receveur mutable. Les signatures
exigent respectivement `&self -> &T` et `&mut self -> &mut T`, sans autre
argument et avec la même cible `T`. La méthode requise doit exister.

L’opérande est évalué une fois. Le résultat désigne une place empruntée, sans
transférer sa responsabilité de destruction. Les règles de mutation, de durée
de vie et de verrou existantes continuent de s’appliquer. Le compilateur ne
crée aucun verrou. Voir le [document anglais](DEREFERENCE.md) pour l’exemple
complet et les détails de résolution.
