[English](FILE.md)

# File et assembleur intégré

Les fichiers sont synchrones par défaut (`std::io::File`). La variante asynchrone
explicite est `std::io::asyn::File`. FileMode, FilePerm, FileStats et SeekFrom restent dans
`std::io`. Les opérations async s’exécutent sur des workers bloquants.


Le frontend Rust et le backend C intègrent `@unchecked`, `addr` et
`usize` déduit de la cible. `@asm` couvre Linux x86-64 et macOS et Windows sur x86-64 et ARM64. Les opérandes entiers de `mov` deviennent des accès mémoire Intel ou des chargements et écritures ARM64. Le bloc `@asm` doit être dans un `@unchecked`.

Le [snippet complet pour Linux x86-64](FILE.md#linux-x86-64-example) montre l’ouverture en lecture, une lecture de huit octets au plus et la fermeture à la sortie du scope.

`File::open(path, mode)` ouvre un fichier existant. Un mode d’accès comme
`FileMode::WRITE_ONLY` peut être combiné avec `FileMode::APPEND` ou
`FileMode::TRUNCATE` via `|`. `File::create(path, mode, perm)`
ouvre ou crée un fichier ; EXCLUSIVE et TRUNCATE sont explicites. `FilePerm.DefaultMode` utilise la politique
de la plateforme. `FilePerm.Perm(0x180)` demande lecture et écriture
pour le propriétaire (`0600` en octal). Linux tient compte du masque de
création ou de l’ACL POSIX par défaut. macOS bloque l’héritage de l’ACL et
applique le masque de création. Windows applique dès la création une ACL
protégée pour le compte effectif, son groupe principal et le reste des
utilisateurs.

La bibliothèque vérifie les droits demandés sur le handle obtenu avant
de le remettre à l’appelant. Si cette vérification échoue, elle renvoie
une erreur système et un fichier vide peut rester au chemin demandé.

`write` renvoie le nombre d’octets écrits. `stats()`
interroge le fichier ouvert et `stats.size()` renvoie sa taille en octets.
`File::delete(path)` supprime l’entrée du fichier.

`file.seek(from)` change la position dans le fichier et renvoie sa valeur
absolue en octets. `SeekFrom.Start(offset)` part du début,
`SeekFrom.Current(offset)` de la position actuelle et `SeekFrom.End(offset)`
de la fin. Les offsets sont des `i64`. Un déplacement au-delà de la fin
laisse la taille intacte. Un offset absolu négatif renvoie `InvalidOptions`.

`File::rename(source, destination)` change le nom sur le même système de
fichiers. Un fichier de destination existant est remplacé si le système
l’autorise. Les deux chemins suivent la même convention que `open`.

`std::io::asyn::File` fournit les mêmes opérations avec `.await` sur les
threads bloquants du runtime. Son `FileError` ajoute `LaunchFailed`.

`std::io::File` sélectionne à la compilation `std::sys::unix::File` sur
Linux x86-64 et macOS, ou `std::sys::win::File` sur Windows. Le type
interne possède la ressource et la ferme via son destructeur. Linux appelle le noyau, macOS appelle libSystem et Windows appelle Win32 depuis `@asm`. Windows convertit le chemin UTF-8 en UTF-16, puis possède le `HANDLE` renvoyé par `CreateFileW` et le ferme avec `CloseHandle`.

Le chemin est un `&str` sans terminateur NUL. Un chemin vide, contenant un NUL
ou dépassant 32767 octets UTF-8 renvoie `InvalidPath`. Les erreurs renvoient `Os { code }` avec un errno négatif sur Unix ou un code Win32 négatif sous Windows. La longueur de la tranche mutable
fixe le budget de lecture. Un buffer vide ou une fin de fichier donne
`Ok(0)`.

- `@unchecked { ... }` marque les effets hors de portée de l’analyse statique que le développeur prend en charge. Les vérifications ordinaires du code Corbo restent actives. Si l’assembleur transmet l’adresse d’un buffer à un thread, le développeur doit garder le buffer valide jusqu’au dernier accès de ce thread, même après la sortie du bloc.
- `@asm { ... }` contient uniquement de l’assembleur de la cible. L’opérande `${nom}` désigne une liaison Corbo visible. Les instructions expriment les transferts. `mov rdi, ${adresse}` lit la liaison et `mov ${raw}, rax` écrit dans la liaison mutable.
- `usize` est un primitif entier non signé de la largeur des pointeurs de la cible. Le compilateur déduit cette largeur de la même configuration de cible que celle utilisée par `#(if: ...)`. Le type est disponible partout.
- Dans l’exemple, `addr` expose l’adresse d’un octet sous forme de `usize`. Le vérificateur suit l’origine dans les opérations Corbo prises en charge, y compris quand l’adresse est utilisée comme opérande. L’auteur du bloc garantit la durée de vie des accès qui se prolongent après sa sortie.

### Confinement des adresses brutes

La règle retenue réserve `addr(référence)` au code situé dans un bloc
`@unchecked`. L’adresse brute reste dans le bloc qui l’a créée. Le compilateur
refuse de la retourner, de l’affecter à une liaison extérieure ou de l’insérer
dans une valeur qui sort du bloc. Copier l’adresse, la convertir en entier
comme `usize` ou la placer dans un agrégat conserve cette restriction. Un
résultat numérique ordinaire, comme le nombre d’octets lu par un appel système,
peut sortir. Dans le code vérifié, `usize` est un entier non signé ordinaire de
la largeur des pointeurs de la cible.

Cette règle porte sur les valeurs que le code Corbo fait passer à la frontière
du bloc. Si l’assembleur ou un appel externe conserve une adresse, l’auteur
du bloc reste responsable de la validité de la cible jusqu’au dernier accès
externe.

Les deux compilateurs vérifient cette frontière. Dans la bibliothèque standard,
le code des fichiers, des sockets, des réacteurs, de l’aléa système, de
l’assembleur cryptographique et des liaisons OpenSSL calcule ses adresses dans
les blocs qui les utilisent.

## Passage des opérandes à l’assembleur

Une entrée `${nom}` fournit la valeur de la liaison Corbo. Un `mov ${raw}, rax`
écrit le résultat dans la liaison mutable `raw`. Dans le schéma x86-64
implémenté ici, une routine assembleur séparée accède à des emplacements à offsets fixes depuis
`r12`. Le bloc laisse `r12` intact, donc les emplacements restent accessibles
quand les `push` et les `pop` déplacent `rsp`. Sur ARM64, la base stable est `x19`. Le backend prévoit l’espace
nécessaire aux sauvegardes et protège les données qui pourraient l’occuper.

Le backend initialise les emplacements depuis les liaisons Corbo avant
l’appel et recopie les sorties écrites par `mov` après l’appel. Chaque liaison
a un emplacement. Un transfert entre deux opérandes Corbo passe par un
registre intermédiaire.

Le bloc restaure le pointeur de pile, les flags et les registres qu’il modifie.
Il écrit le résultat avant de restaurer `rax`. Les octets écrits par le noyau
restent dans le buffer après la restauration.

Par défaut, le backend suppose que `@asm` peut lire et écrire la mémoire
accessible. Aucune annotation d’effet n’est requise. Une lecture Corbo après
`read` doit pouvoir observer les octets écrits par le noyau. Dans `@unchecked`,
l’auteur du bloc garantit la validité des adresses et le respect des bornes.

Dans `File::read`, `addr(&buffer[0])` fournit l’adresse du premier octet.
L’adresse est la même avec une référence partagée ou mutable. La permission
de modifier le slice est exprimée par `buffer: &mut [u8]` dans la signature.
Le bloc passe l’adresse et la longueur séparément. Le test du buffer vide
précède la prise d’adresse.

## Entrées/sorties à position explicite

`std::io::File` et `std::io::asyn::File` proposent `read_at(&self, buffer: &mut [u8], offset: u64)`
et `write_at(&self, buffer: &[u8], offset: u64)`, avec `Result<usize, FileError>` en retour.
Les variantes asynchrones exigent `.await`. Le curseur séquentiel reste inchangé,
y compris après une erreur. Les transferts peuvent être partiels ; EOF et les
tranches vides à une position valide renvoient zéro. La position et la fin de
la plage doivent tenir dans un `i64`, sinon `InvalidOptions` est renvoyé.
La lecture en mode écriture seule, l’écriture en lecture seule et `write_at`
en mode append sont refusés.

Unix utilise `pread`/`pwrite` et réessaie après EINTR. Sous Windows, File possède
un HANDLE séquentiel et un HANDLE compagnon OVERLAPPED créé dès l’ouverture.
Chaque opération positionnée utilise son propre événement de fin, conservé
jusqu’à la fin de ReadFile/WriteFile puis fermé. Les périphériques spéciaux ne permettant pas ce compagnon peuvent être refusés
à l’ouverture. Les deux HANDLEs du fichier sont fermés à sa destruction, y compris après un move. La création anticipée
du compagnon préserve l’identité du fichier après renommage. Les variantes
async utilisent les workers bloquants existants et retiennent les emprunts
jusqu’à la fin de l’opération.

[Validation ciblée](cycles/FILE_POSITIONED_CYCLE.md).

## Chemins texte et flags combinables

Les chemins de `open`, `create`, `rename` et `delete` sont des `&str` UTF-8,
sans NUL final, y compris dans `std::io::asyn`. L’API ajoute le terminateur dans
son tampon interne. Un chemin vide, contenant un NUL ou dépassant 32767 octets
est refusé. Le backend privé `std::sys` conserve ses chemins binaires terminés.

READ et WRITE se combinent avec `|`. CREATE conserve le contenu d’un fichier
existant ; TRUNCATE le vide explicitement. CREATE_NEW vaut CREATE | EXCLUSIVE.
SYNC demande des écritures synchrones au système. `create(path, flags, perm)`
ajoute CREATE et conserve FilePerm, sans troncature ni exclusivité implicites.
Les anciens noms READ_ONLY, WRITE_ONLY et READ_WRITE restent des alias.
