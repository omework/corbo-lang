[English](SCOPE_EXIT.md)

# Sortie d'un bloc : contrat et traduction en C

Cette étape concerne la sortie normale d'un bloc et `return`, dans le
sous-ensemble actuel de Corbo. Elle ne couvre pas le déroulement après un arrêt
sur erreur, les destructeurs utilisateur ou des branches avec effets mémoire.

## Règle de nettoyage

P3–P4, L3–L4 et L7 précisent le modèle de la data stack implicite. Le
receveur d’un transfert dispose d’un emplacement dans une plage durable
avant la construction. Les dépendances du destructeur fixent l’ordre
des destructions. Après le nettoyage, le curseur de la plage enfant
revient à sa position d’entrée. Pour un pool typé, un slot détruit peut
être réutilisé indépendamment de ce recul. Les exemples ci-dessous
emploient la syntaxe historique de sources explicites.

À chaque sortie de bloc, le compilateur :

1. Rattache au parent les allocations explicitement transférées. Leur source
   doit survivre à ce transfert. La réception les ajoute à l'ordre du parent,
   en conservant l'ordre relatif des allocations transférées ensemble.
2. Détruit les allocations encore vivantes rattachées au bloc, en ordre inverse
   de création ou réception. Une allocation déjà consommée par `drop` est ignorée.
3. Ferme les sources créées dans le bloc, en ordre inverse de déclaration,
   après avoir vérifié qu'elles ne fournissent plus aucune allocation vivante.
   Une source reçue par emprunt n'est pas fermée ici.

Un `return` quitte successivement les blocs englobants jusqu'à la fonction.
Chaque bloc applique cette même règle. Si le retour transfère une allocation,
elle traverse ces frontières sans être détruite ; le receveur de l'appel en
assurera ensuite le nettoyage. Un retour scalaire conserve sa valeur pendant
le nettoyage. Les instructions après le retour ne sont pas émises.

## Exemple vérifiable

Le programme complet est dans [examples/scope_exit.crb](../examples/scope_exit.crb).

```rust
fn create(memory: &mut Allocator) -> <- Int {
    let mut outer = new(memory) Int(1);
    {
        let mut inner = new(memory) Int(2);
        {
            let mut result = new(memory) Int(3);
            return <- result;
        }
    }
}

fn main() {
    let mut memory = Pool<Int>::new(3);
    let mut received = create(&mut memory);
    print(received);
}
```

| Événement | Nettoyage |
| --- | --- |
| Sortie du bloc de `result` | `result` est transféré, il reste vivant |
| Sortie du bloc de `inner` | Destruction de `inner` |
| Sortie de `create` | Destruction de `outer`, retour de `result` |
| Suite de `main` | Affichage de `3` |
| Sortie de `main` | Destruction de `result`, fermeture du pool |

Le C émis suit cette séquence. En renommant les variables générées et en
omettant les variables intermédiaires :

```c
static Cell *create(Source *memory) {
    Cell *outer = cell_new(memory, 1, "outer");
    Cell *inner = cell_new(memory, 2, "inner");
    Cell *result = cell_new(memory, 3, "result");
    cell_drop(inner);
    cell_drop(outer);
    return result;
}

/* Dans le point d'entrée : */
Source memory = source_pool(3);
Cell *received = create(&memory);
printf("%d\n", received->value);
cell_drop(received);
source_close(&memory);
```

Le transfert ne copie pas l'objet : le pointeur retourné conserve son adresse.
Les appels de nettoyage sont insérés avant le `return` C ; C ne les ajoute pas
automatiquement.

## Destruction et récupération du stockage

`cell_drop` exécute d'abord la destruction de démonstration (la trace `destroy`),
puis marque l'objet mort et récupère son stockage selon sa source :

| Source | Après destruction |
| --- | --- |
| `allocator()` | Appel de `free` sur l'allocation |
| `stack(...)` | Recul du curseur sur le suffixe mort ; les trous intérieurs attendent |
| `Pool<T>::new(...)` | Slot libre réutilisable ; recul du curseur sur le suffixe mort |

Dans l'exemple, `result` est physiquement au-dessus de `inner` et `outer`.
Leur destruction ne permet donc pas encore de reculer le curseur. Quand
`result` est détruit dans `main`, les trois slots forment un suffixe mort :
le runtime récupère successivement `result`, `inner`, puis `outer`.
Cette récupération ne relance aucun destructeur.

`source_close` libère ensuite le mapping virtuel des stacks et pools via
`munmap`. Elle exige une source vide ; elle ne remplace pas la destruction des
objets. Les octets n'ont pas besoin d'être effacés pour rendre les slots libres.

## Validation

[tests/test_scope_exit.py](../tests/test_scope_exit.py) compare les traces du C
compilé et exécuté aux ordres attendus : sorties normales, retours Void,
scalaires et allocations depuis des blocs imbriqués, `drop` anticipé, ordre de
réception, fermeture d'une source privée et refus d'un retour dont la source
expire. Les séquences principales sont exécutées avec les trois sources.
Un test inspecte aussi l'absence d'une allocation située après `return`.

Ces tests relient cette règle au C exécuté pour des cas précis ; ils ne
constituent pas une preuve pour tous les programmes acceptés. Le périmètre
global reste décrit dans [SAFETY.md](SAFETY.md).
