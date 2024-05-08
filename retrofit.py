import argparse
import gzip
import json
import math
import numpy
import re
import sys

from copy import deepcopy

from morphdata import MorphPair

isNumber = re.compile(r'\d+.*')
def norm_word(word):
  if isNumber.search(word.lower()):
    return '---num---'
  elif re.sub(r'\W+', '', word) == '':
    return '---punc---'
  else:
    return word.lower()

''' Read all the word vectors and normalize them '''
def read_word_vecs(filename):
  wordVectors = {}
  if filename.endswith('.gz'): fileObject = gzip.open(filename, 'r')
  else: fileObject = open(filename, 'r')

  for line in fileObject:
    try:
      line = line.strip().lower()
      word = line.split()[0]
      wordVectors[word] = numpy.zeros(len(line.split())-1, dtype=float)
      for index, vecVal in enumerate(line.split()[1:]):
        wordVectors[word][index] = float(vecVal)
      ''' normalize weight vector '''
      wordVectors[word] /= math.sqrt((wordVectors[word]**2).sum() + 1e-6)
    except ValueError as e:
      print(e)
      print(line)

  sys.stderr.write("Vectors read from: "+filename+" \n")
  return wordVectors

''' Write word vectors to file '''
def print_word_vecs(wordVectors, outFileName):
  sys.stderr.write('\nWriting down the vectors in '+outFileName+'\n')
  outFile = open(outFileName, 'w')
  for word, values in wordVectors.items():
    outFile.write(word+' ')
    for val in wordVectors[word]:
      outFile.write('%.4f' %(val)+' ')
    outFile.write('\n')
  outFile.close()

''' Read the PPDB word relations as a dictionary '''
def read_lexicon(filename):
  lexicon = {}
  for line in open(filename, 'r'):
    words = line.lower().strip().split()
    lexicon[norm_word(words[0])] = [norm_word(word) for word in words[1:]]
  return lexicon

def read_transforms(filename):
  '''Read transform data from file.

  Return as dict of (pattern -> list of word form pairs).

  '''
  with open(filename) as transforms_file:
    transforms = [
      MorphPair(
        norm_word(transform[0]),
        norm_word(transform[1]),
        transform[2],
      )
      for transform in json.load(transforms_file)
    ]

  sys.stderr.write(f"Transforms read from: {filename} \n")

  return transforms

def get_all_transform_forms(transforms):
  '''Get list of all word forms in transform data.'''
  forms = set()
  for transform in transforms:
    forms.add(transform.pre)
    forms.add(transform.post)

  return forms

def get_transforms_containing_form(transforms, form):
  '''TODO'''
  return [
    transform for transform in transforms
    if form == transform.pre
    or form == transform.post
  ]


def compute_average_alignments(transforms, wordVecs):
  sums = dict()
  counts = dict()
  for trans in transforms:
    if trans.pre in wordVecs and trans.post in wordVecs:
      if trans.pattern not in sums:
        sums[trans.pattern] = wordVecs[trans.post] - wordVecs[trans.pre]
        counts[trans.pattern] = 1
      else:
        sums[trans.pattern] += wordVecs[trans.post] - wordVecs[trans.pre]
        counts[trans.pattern] += 1

  averages = dict()
  for pattern in sums.keys():
    averages[pattern] = sums[pattern] / counts[pattern]

  return averages

''' Retrofit word vectors to a lexicon '''
def retrofit(wordVecs, numIters, lexicon=None, transforms=None):
  newWordVecs = deepcopy(wordVecs)
  wvVocab = set(newWordVecs.keys())
  retroDataVocab = set()
  if lexicon:
    retroDataVocab |= set(lexicon.keys())
  if transforms:
    retroDataVocab |= set(get_all_transform_forms(transforms))
  loopVocab = wvVocab & retroDataVocab
  for it in range(numIters):
    sys.stderr.write(f"Iteration {it+1}\n")

    if transforms:
        averageAlignments = compute_average_alignments(transforms, wordVecs)

    # loop through every node also in ontology (else just use data estimate)
    for word in loopVocab:
      if lexicon and word in lexicon:
        wordNeighbours = set(lexicon[word]).intersection(wvVocab)
        numNeighbours = len(wordNeighbours)
      else:
        wordNeighbours = []
        numNeighbours = 0

      if transforms:
        wordTransforms = get_transforms_containing_form(transforms, word)
        # filter pairs with OOV members
        wordTransforms = [
          transform for transform in wordTransforms
          if transform.pre in loopVocab
          and transform.post in loopVocab
        ]
        numTransforms = len(wordTransforms)

      #no neighbours, pass - use data estimate
      if (
          lexicon and numNeighbours == 0 and transforms and numTransforms == 0
          or lexicon and numNeighbours == 0
          or transforms and numTransforms == 0
      ):
        continue

      # the weight of the data estimate if the number of neighbours
      weight = 0
      if lexicon:
        weight += numNeighbours
      if transforms:
        weight += numTransforms
      newVec = weight * wordVecs[word]

      if lexicon:
        # loop over neighbours and add to new vector (currently with weight 1)
        for ppWord in wordNeighbours:
          newVec += newWordVecs[ppWord]

      if transforms:
        # loop over patterns and add what the vector *would* be if that pattern was the only
        # thing determining it's values
        for transform in wordTransforms:
          # If the current word is the pre-transformation member of the pair, we want to
          # target the vector obtained by going backwards from the post-transformation form
          # to the pre-transformation form.
          if word == transform.pre:
            target = newWordVecs[transform.post] - averageAlignments[transform.pattern]
          # If the current word is the post-transformation member of the pair, we want to
          # target the vector obtained by going forwards from the pre-transformation form to
          # the post-transformation form.
          elif word == transform.post:
            target = newWordVecs[transform.pre] + averageAlignments[transform.pattern]
          # Otherwise, something has gone wrong!
          else:
            raise ValueError(f"'{word}' not in transform pair {transform}")

          newVec += target

      newWordVecs[word] = newVec/(2*weight)

  return newWordVecs

if __name__=='__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--input", type=str, default=None, help="Input word vecs")
  parser.add_argument("-l", "--lexicon", type=str, default=None, help="Lexicon file name")
  parser.add_argument("-t", "--transforms", type=str, default=None, help="Morphological transforms index file name")
  parser.add_argument("-o", "--output", type=str, help="Output word vecs")
  parser.add_argument("-n", "--numiter", type=int, default=10, help="Num iterations")
  args = parser.parse_args()

  if args.lexicon is None and args.transforms is None:
    sys.stderr.write("Must supply one or both of -l/--lexicon or -t/--transforms.\n")
    parser.print_usage(sys.stderr)
    sys.exit()

  wordVecs = read_word_vecs(args.input)
  if args.lexicon:
    lexicon = read_lexicon(args.lexicon)
  else:
    lexicon = None
  if args.transforms:
    transforms = read_transforms(args.transforms)
  else:
    transforms = None
  numIter = int(args.numiter)
  outFileName = args.output

  ''' Enrich the word vectors using ppdb and print the enriched vectors '''
  print_word_vecs(retrofit(wordVecs, numIter, lexicon, transforms), outFileName)
