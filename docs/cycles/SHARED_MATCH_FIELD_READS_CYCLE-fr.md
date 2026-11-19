[English](SHARED_MATCH_FIELD_READS_CYCLE.md)

# Lectures de champs dans un match partagé

Le cas déjà enregistré dans `validation/open-shared-enum-descendant-read.crust`
était refusé par un filtre syntaxique du match : il reconnaissait `*nom`, mais
pas `*nom.champ`. Les règles F2 et les règles ordinaires de lecture et d'emprunt
ne font pas cette distinction. Aucune règle normative n'est modifiée.

Le filtre reconnaît désormais le déréférencement de champ. Les déclarations
intermédiaires utilisent le même prédicat que l'expression finale, y compris
pour les calculs arithmétiques. Le vérificateur normal reste chargé du type,
de l'existence du champ et de la validité des références.

Trois méthodes ciblées passent à O0 en 1,622 s, code 0. Elles exécutent quatre
programmes : lecture directe, variable intermédiaire, calcul, puis utilisation
du résultat Int après destruction du porteur et de sa cible. Un champ inexistant
reste refusé par verify_program et compile_source. Journal :
`validation/shared-match-field-reads-o0.log`. Le refus initial des deux entrées
est conservé dans `validation/shared-match-field-reads-before.log`.

La régression directement liée à O2 passe 64 méthodes en 28,099 s, processus
terminé avec code 0. Elle couvre les champs empruntés, les matchs mutables et
leurs appels, les matchs consommateurs async et les effets suspendus d'enums.
Journal : `validation/shared-match-field-reads-regression-o2.log`.

Les exécutions natives ciblées utilisent Clang C11, pthread et UBSan sans
récupération. Cette passe concerne les lectures Int déjà prises en charge ;
elle ne généralise pas toutes les expressions et signatures de fonctions dans
les bras. Aucune campagne adversariale ou de mutations n'a été ajoutée.

```sh
PYTHONPATH=tests:. CRUST_TEST_OPT=-O0 python3 -m unittest test_shared_match_field_reads -v
PYTHONPATH=tests:. CRUST_TEST_OPT=-O2 CRUST_SANITIZE=undefined python3 -m unittest test_shared_match_field_reads test_reference_fields test_mutable_match test_mutable_match_calls test_async_consuming_enum_match test_async_enum_suspension_fields -v
```

Snapshot : `/tmp/crust-before-shared-match-field-reads/`.
Patch : `validation/shared-match-field-reads-crust.py.patch`.
