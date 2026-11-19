"""Compare the Rust syntax projection against the existing corpus, without rule checks."""
import argparse
from collections import Counter
from itertools import zip_longest
import json
from pathlib import Path
import subprocess

from build_representation_corpus import ROOT, candidates

MODES = {
    'programme ou déclarations': 'program',
    'fragment de bloc': 'block',
    'fragment de signature': 'signature',
}
FACTS = {'déplacement': 'move', 'pool': 'pool', 'référence': 'borrow', 'adresse candidate': 'address'}


def normalized_tokens(words):
    output = []
    for word in words:
        if word == '::':
            output.extend((':', ':'))
        elif word.startswith('>') and len(word) > 1 and all(c in '>=' for c in word):
            output.extend(word)
        else:
            output.append(word)
    return output


def reference_scopes(row):
    tokens = row['tokens']
    return [[scope['parent'], tokens[scope['entrée']]['ligne']]
            for scope in row['scopes'][1:] if scope['entrée'] < len(tokens)]


def reference_bindings(row):
    objects = row['objets']
    return [fact['nom'] for fact in row['faits'] if fact['sorte'] == 'liaison'
            and objects[fact['nœud']].get('op') == 'var' and fact['nom'] != '_']


def reference_moves(row):
    facts = row['faits']
    return [[fact['nom'], str(facts[fact['source']]['scope']) if fact['source'] is not None else '',
             str(facts[fact['destination']]['scope'])]
            for fact in facts if fact['sorte'] == 'déplacement']


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--bin', type=Path, default=ROOT / 'build/rust_frontend/debug/corbo-frontend')
    cli.add_argument('--corpus', type=Path, default=ROOT / 'build/representation_corpus.jsonl')
    cli.add_argument('--report', type=Path, default=ROOT / 'build/rust_frontend_comparison.jsonl')
    args = cli.parse_args()
    inputs = []
    with args.corpus.open() as corpus:
        for candidate, line in zip_longest(candidates(), corpus):
            if candidate is None or line is None:
                raise SystemExit('Corpus et inventaire désalignés. Régénérer le corpus.')
            path, start, origin, source = candidate
            row = json.loads(line)
            if (row['fichier'], row['ligne_source'], row['origine']) != (str(path.relative_to(ROOT)), start, origin):
                raise SystemExit('Corpus et inventaire désalignés. Régénérer le corpus.')
            if mode := MODES.get(row['statut']):
                inputs.append((row, mode, source))
    request = ''.join(f'{mode}\t{source.encode().hex()}\n' for _, mode, source in inputs)
    run = subprocess.run([str(args.bin.resolve()), '--batch'], input=request, text=True,
                         stdout=subprocess.PIPE, check=True)
    counts = Counter()
    with args.report.open('w') as report:
        for entry, response in zip(inputs, run.stdout.splitlines(), strict=True):
            row, mode, source = entry
            result, *data = response.split('\t')
            origin = row['origine']
            counts[origin, 'référence'] += 1
            record = {key: row[key] for key in ('fichier', 'ligne_source', 'origine')}
            if result == 'ERR':
                offset, message = data
                offset = int(offset)
                record.update(diagnostic=message, octet=offset,
                              ligne=source.encode()[:offset].count(b'\n') + 1,
                              extrait=source.encode()[offset:offset + 70].decode(errors='replace'))
                counts[origin, 'refus Rust'] += 1
            else:
                tokens, scopes, bindings, facts, moves = data
                rust_tokens = normalized_tokens(bytes.fromhex(token).decode() for token in tokens.split(',') if token)
                checks = {
                    'tokens': (normalized_tokens(token['lexème'] for token in row['tokens']), rust_tokens),
                    'scopes': (reference_scopes(row), [[int(part) for part in scope.split(':')]
                                                      for scope in scopes.split(',') if scope]),
                    'liaisons': (reference_bindings(row), bindings.split(',') if bindings else []),
                    'faits': (Counter(FACTS[fact['sorte']] for fact in row['faits'] if fact['sorte'] in FACTS),
                              Counter(facts.split(',') if facts else [])),
                    'liens move': (reference_moves(row), [move.split(':') for move in moves.split(',') if move]),
                }
                counts[origin, 'accepté Rust'] += 1
                for name, (reference, actual) in checks.items():
                    if reference == actual:
                        counts[origin, f'{name} égaux'] += 1
                    else:
                        record[name] = {'python': reference, 'rust': actual}
                if all(reference == actual for reference, actual in checks.values()):
                    counts[origin, 'projection égale'] += 1
            report.write(json.dumps(record, ensure_ascii=False) + '\n')
    for (origin, name), count in sorted(counts.items()):
        print(f'{origin}\t{name}\t{count}')
    print(args.report)


if __name__ == '__main__':
    main()
