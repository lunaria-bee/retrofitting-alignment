#!/usr/bin/env python3


import argparse
from collections import namedtuple
import json
from pathlib import Path
import sys


CATVAR_MORPH_PATH = Path('./catvar/English-Morph.txt')
OUTPUT_PATH = Path('./alignment/catvar.json')


parser = argparse.ArgumentParser()


parser.add_argument(
    '-o',
    dest='output_path',
    metavar="OUTPUT_FILE",
    type=Path,
    default=OUTPUT_PATH,
    help="Path to output file. Will be created or overwritten.",
)


MorphRelation = namedtuple('MorphRelation', ('forms', 'base', 'pattern'))


def get_morphs(path=CATVAR_MORPH_PATH):
    with open(path) as morph_file:
        morphs = []
        for line in morph_file.readlines():
            split = line.strip().split('\t')
            morphs.append(MorphRelation(split[:-2], split[-2], split[-1]))

    return morphs


def search_morphs(morphs, forms=None, base=None, pattern=None, mode='&'):
    '''Search morphs based on string patterns in item elements.

    `morphs`: Iterable of MorphRelation objects.
    `forms`: Item(s) to search for in each MorphRelation.forms field.
    `base`: Item to search for in each MorphRelation.base field.
    `pattern`: Item to search for in each MorphRelation.pattern field.
    `mode`: Either '&' or '|'. Indicates whether to return only results that match all
            given criteria ('&') or to return those that match any given criterion ('|').

    Return: List of matching morphs.

    '''
    if isinstance(forms, str):
        forms = set([forms])
    elif forms is not None:
        forms = set(forms)

    results = []
    test_function = (all if mode == '&' else any)
    return [
        morph for morph in morphs
        if test_function([
                forms is None or forms & set(morph.forms),
                base is None or base == morph.base,
                pattern is None or pattern == morph.pattern,
        ])
    ]


def build_index(morphs):
    index = dict()
    for morph in morphs:
        if morph.pattern not in index:
            index[morph.pattern] = set()
            index['r' + morph.pattern] = set()

        for form in morph.forms:
            index[morph.pattern].add((morph.base, form))
            index['r' + morph.pattern].add((form, morph.base))

    index = {key: list(value) for key, value in index.items()}

    return index


def main(argv):
    args = parser.parse_args(argv)

    morphs = get_morphs()
    alignment_index = build_index(morphs)
    args.output_path.parent.mkdir(exist_ok=True)
    with open(args.output_path, 'w') as output_file:
        json.dump(alignment_index, output_file)


if __name__ == '__main__': main(sys.argv[1:])

