[English](FOUNDATIONS_AND_VECTORS.md)

# Fondamentaux, allocations typées et vecteurs

Décisions du chantier suivant String. Les identifiants ci-dessous servent à
rattacher le comportement attendu à la matrice de vérification.

## Types, effets et contrôle

- **F1 — Taille finie.** Une définition récursive est admise si chaque cycle
  traverse une indirection de taille connue, par exemple `A<T>` ou `&T`.
  Un cycle de champs stockés directement est refusé.
- **F2 — Match.** Un match couvre chaque variante ou les variantes restantes
  via `_`. Un match consommant exige `match (-> valeur)`. Le bras reçoit
  les valeurs déplacées. Un match par emprunt lie les champs selon le mode
  partagé ou mutable du sujet. Les bras qui fournissent un résultat
  s'accordent sur son type. Un bras qui quitte la fonction ne fournit pas
  de résultat à la jonction. Un motif consommant `_` est refusé s'il écarte
  une allocation possédée, y compris lorsqu'il masque une variante entière.
  Le bras lie le contenu propriétaire à un nom ayant un usage explicite
  possible (U1, brouillon 01). Le contrôle porte sur le type, même lorsque
  la variante produite est connue.
- **F3 — Jonctions et sorties.** Une utilisation après une jonction est
  admise si elle est valide sur chaque chemin qui l'atteint. Une reprise
  de boucle doit satisfaire les conditions de l'itération suivante. Une
  sortie rejoint les autres chemins de sortie, y compris la possibilité de
  zéro itération pour un `while`. Le résultat d'un retour est évalué et
  transféré avant le nettoyage, de l'intérieur vers l'extérieur, puis
  l'appelant reprend. Voir S4, S5, S5a, T9 et T10.
- **F4 — Ordre et court-circuit.** Les arguments sont évalués de gauche à
  droite et un déplacement prend effet avant l'argument suivant (B4a).
  `&&` évalue son opérande droit seulement si le gauche est vrai. `||`
  l'évalue seulement si le gauche est faux. L'analyse des effets suit les
  chemins d'évaluation possibles.
- **F5 — Arithmétique contrôlée.** Les opérations entières donnent un
  résultat représentable ou échouent. Un échec établi à la compilation est
  diagnostiqué statiquement. Une division par zéro ou un débordement
  déterminé à l'exécution arrête le programme avec un diagnostic avant
  l'opération C dangereuse.
  Pour les conversions entières, `as` est réservé aux conversions
  qui préservent toutes les valeurs du type source, même si l’expression
  convertie est une constante. Un littéral représentable peut recevoir
  directement un type, par exemple `let octet: u8 = 42;`.
  Les autres conversions utilisent `try_from` et rendent un `Result` :
  `u8::try_from(n)` réussit pour `0..=255` et signale une erreur sinon.
  Le [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#conversions-entre-entiers-et-flottants)
  applique le même critère d'exactitude entre les types flottants et
  entre entiers et flottants.
  Pour l'arithmétique flottante, le
  [brouillon 07](../design-buffer/07-conversions-resultats-copies-et-vues.md#opérateurs-arithmétiques)
  définit l'arrondi des résultats et les cas où le calcul échoue.

## Allocation explicite

- **H1 — Représentation.** `Pool<T>.new(...)` fournit un `A<T>`, une
  valeur non Copy qui désigne l'objet initialisé et son pool d'origine.
  Le déplacement transmet ces deux informations et la responsabilité
  unique du nettoyage, avec la même adresse d'objet. Le pool doit
  survivre à tout receveur de cette responsabilité.
- **H2 — Accès.** `*a` lit par copie si `T` est Copy. Déplacer un
  contenu non Copy hors de `A<T>` est refusé. `ref()` et `mut_ref()`
  empruntent le handle, `vref()` et `mut_vref()` empruntent le contenu.
  Un `&mut A<T>` permet de remplacer le handle après évaluation du
  remplaçant, avec nettoyage de l'ancienne allocation. Un `&mut T`
  permet de modifier le contenu à la même adresse.
- **H3 — Méthodes.** Les méthodes et les crochets s'utilisent directement
  sur la variable d'allocation. Le type d'un élément lu reste celui de
  l'élément déclaré, y compris s'il s'agit d'un autre handle. Un
  receveur consommant distingue `self: -> A<T>` de `self: -> T`.
  L'appel consommant s'écrit `(-> a).methode()`. Pour un contenu
  comparable, `a.vequals(b.ref())` compare les contenus.

## Vecteurs

- **VE1 — Stockage homogène.** Un `Vector<T>` contient un préfixe
  initialisé de cases de type `T` et commence vide, même si `T` n'a
  pas de valeur par défaut. `Vector<Int>` stocke les valeurs dans ses
  cases. `Vector<A<Int>>` stocke les handles. Un vecteur d'emprunts
  stocke les emprunts et propage leurs contraintes. Il ne nettoie pas
  leurs cibles. Le type des cases est fixé sans inférence de pool ni
  conversion automatique entre valeur et handle.
- **VE2 — Insertion et destruction.** `push` copie un élément Copy et
  reçoit par transfert explicite un élément non Copy. Une case recevant
  un `A<T>` prend en charge son nettoyage auprès de son pool d'origine.
  Deux cases peuvent donc désigner des pools différents. Déplacer un
  emprunt mutable dans une case préserve son exclusivité. Détruire le
  vecteur nettoie ses éléments présents avant de récupérer son stockage.
- **VE3 — Extraction et remplacement.** `pop` produit `Option<T>`.
  `remove` conserve l'ordre des éléments restants et signale un index
  invalide. Les réarrangements décalent les cases concernées sous réserve
  des emprunts en cours. Déplacer une case de handles laisse leurs cibles
  à la même adresse. `replace(index, -> valeur)` renvoie l'ancienne
  valeur en cas de succès, ou l'entrante en cas d'index invalide, sans
  modifier le vecteur dans ce dernier cas. La nouvelle valeur est prête
  avant le remplacement. Chaque handle extrait conserve sa provenance et
  un résultat non Copy exige un transfert explicite. Le résultat propriétaire
  peut être consommé directement avec `drop(-> opération(...))` : l'opération
  est évaluée d'abord, puis son contenu possédé est détruit une seule fois
  avant l'instruction suivante, quel que soit le pool d'origine.
- **VE4 — Bornes et publication.** `try_push(-> valeur)` restitue la
  valeur entrante si le vecteur est plein. Le Result propriétaire impose U1
  même lorsque la réussite est connue ; drop ne détruit que le contenu
  possédé par la variante effectivement produite. Pour les octets, `try_extend`
  publie le bloc entier ou laisse le vecteur intact avec
  `CapacityExceeded`. Les écritures au-delà de la longueur ne deviennent
  accessibles qu'une fois initialisées. Une lecture externe peut remplir
  l'espace disponible et distinguer des octets reçus, la fin de flux et
  l'espace épuisé. Une erreur laisse la longueur inchangée. L'emprunt de
  la destination dure tant que le lecteur peut y accéder.
- **VE5 — Tranches.** `&v[debut..fin]` est une vue `&[T]` sur un
  intervalle semi-ouvert vérifié. Les deux tranches mutables de
  `split_at_mut(index)` sont disjointes. L'accès via l'emprunt parent
  est suspendu tant qu'une des deux tranches est encore utilisée.
- **VE6 — Initialisation sur place.** L'API retenue `push_new()`
  initialise une nouvelle case avec la valeur par défaut de `T` et
  renvoie ensuite un emprunt mutable de cette case.

## Placement et chaînes

- **GR1 — Placement.** Le descripteur fixe occupe la data stack
  classique. Le contenu grandit dans une région de la data stack à
  régions. Chaque curseur a un seul sens de croissance.
  L’annotation `stack_region` fixe `max_size` et, facultativement,
  `count`. L’héritage, les transferts et le recours à une stack
  à régions dédiée suivent G1–G12.
- **GR2 — Récupération.** Une région est une sous-stack avec son propre
  curseur. Son nettoyage peut reculer ce curseur après les destructions
  requises. Les régions libérées hors de l'extrémité peuvent être
  indexées pour réemploi. Le curseur externe recule sur une extrémité
  redevenue libre. La croissance d'un vecteur laisse les éléments déjà
  en place à leur adresse.
- **TX21 — Représentation de String.** `String` fournit son API texte
  au-dessus d'un `Vector<u8>` en ligne et conserve l'invariant UTF-8.
  Une vue texte est contiguë dans le sens des adresses croissantes.
- **TX22 — Concaténation.** `push_str(&str)` emprunte le texte source.
  `destination.merge(-> source)` concatène et consomme la String source.
  La responsabilité de nettoyer la source est transférée à l'opération.
  Les limites du stockage restent applicables et l'API ne spécifie
  aucune économie de copie ou de pic mémoire.
