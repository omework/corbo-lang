[English](RESET.md)

# Reset : destruction collective avant réinitialisation

**Document historique de l'implémentation existante.** Le 4 novembre 2026,
l'utilisateur a validé le retrait de `pool.reset()`/`memory.reset()` du prototype
visé : voir [PR1](ASYNC_MULTITHREAD_RULES.md#6-retrait-de-reset-du-prototype).
Le compilateur, les contrats et les tests décrits ici n'ont pas encore été
migrés, conformément à la demande de ne rien implémenter pendant la consignation.
Les résultats passés restent des preuves du comportement antérieur, pas de
l'absence future de cette API.

`memory.reset()` demande explicitement de détruire toutes les allocations encore
vivantes de cette source, puis de rendre son stockage réutilisable. Cette règle
remplace l'ancien reset qui exigeait une source déjà vide.

## Vérification et ordre

Avant toute destruction, le compilateur vérifie les usages futurs des accès
directs et des emprunts, dans les scopes actifs et les fonctions appelantes.
Il refuse le reset si l'un de ces accès doit encore servir. Un réemprunt
temporairement suspendu pendant un appel est lui aussi pris en compte.

```rust
let mut memory = pool<Int>(2);
let mut a = new(memory) Int(10);
let mut b = new(memory) Int(20);
print(a);
memory.reset(); // Détruit b, puis a, et réinitialise le pool.
```

Ajouter `print(a)` après le reset fait refuser ce reset. Il en va de même pour
un usage ultérieur d'un emprunt vers `a`, ou pour un déplacement ou un `drop`.
La dernière utilisation n'entraîne pas à elle seule de destruction ; `reset`
est la demande explicite qui la déclenche ici.

Le nettoyage concerne uniquement cette source. Il parcourt les scopes actifs
du plus profond au plus extérieur, et leurs allocations en ordre inverse de
création/réception. L'ordre n'est pas regroupé par variante d'enum. Les
allocations déjà détruites sont ignorées ; les accès aux allocations détruites
sont invalidés et le nettoyage de fin de bloc ne les détruit pas de nouveau.

## Fonctions et C généré

Recevoir `&mut Allocator` ou `&mut Pool<T>` autorise le reset de la source réelle,
y compris des allocations restées dans les scopes appelants. Un emprunt de
source en lecture ne l'autorise pas. Les fonctions du prototype sont déjà
spécialisées par site d'appel ; le compilateur vérifie donc les allocations et
les usages concernés à ce site.

Par exemple, pour une fonction qui appelle seulement `memory.reset()`, deux
allocations vivantes de l'appelant produisent, après renommage :

```c
static void clear(Source *memory, Cell *a, Cell *b) {
    cell_drop(b);
    cell_drop(a);
    source_reset(memory);
}
```

Les paramètres de nettoyage sont internes au C généré. Ils évitent de référencer
des variables C hors de leur fonction et transmettent les pointeurs nécessaires
aux appels imbriqués. Les [résumés d’effets](EFFECTS.md) déterminent désormais
les sources pouvant réellement subir un reset, y compris transitif. Seules les
allocations pouvant dépendre de ces sources nécessitent ces captures. Une fonction
qui alloue seulement ne les reçoit pas pour les anciennes allocations de cette
source. Cela ne change pas les signatures écrites en Corbo.

La fonction C bas niveau `source_reset` conserve son contrôle de source vide :
les destructions ont déjà été émises avant son appel. Sur le tas elles font les
`free` ; sur les stacks et pools elles libèrent les slots selon les mécanismes
habituels. Le mapping virtuel reste disponible jusqu'à la fermeture de la source.
Réutiliser une adresse après reset ne réactive pas les anciens accès.

## Exemple et tests

[examples/reset.crb](../examples/reset.crb) retourne une allocation depuis une
fonction, détruit collectivement les valeurs via une autre fonction, puis
réutilise le stockage.

[tests/test_reset_transitions.py](../tests/test_reset_transitions.py) couvre les
trois sources, les allocations réaffectées ou transférées, les scopes imbriqués,
les appels et réemprunts, les refus d'accès futurs, les resets répétés, les
pools d'enum et la réutilisation des adresses. Les destructeurs utilisateur,
références stockées dans les objets et branches à effets mémoire restent hors
du sous-ensemble actuel ; ces tests ne constituent pas une preuve générale.
