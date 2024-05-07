import argparse
import gzip
import json
import math
import numpy
import re
import sys

from copy import deepcopy

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

def read_alignment(filename):
  '''Read alignment data from file.

  Return as dict of (pattern -> list of word form pairs).

  '''
  with open(filename) as alignment_file:
    alignment = json.load(alignment_file)

  # Normalize word forms.
  alignment = {
    pattern: [
      [norm_word(pair[0]), norm_word(pair[1])]
      for pair in pairs
    ]
    for pattern, pairs in alignment.items()
  }

  sys.stderr.write(f"Alignment read from: {filename} \n")

  return alignment

def get_all_alignment_forms(alignment):
  '''Get list of all word forms in alignment data.'''
  return set(
    form
    for pattern, pairs in alignment.items()
    for pair in pairs
    for form in pair
  )

def get_alignment_patterns_containing_form(alignment, form):
  '''Get list of alignment patterns containing 'form' in at least one pair.

  Excludes patterns for which all pairs containing the form map a word form to itself
  (i.e. both pair elements are identical).

  '''
  return [
    pattern for pattern, pairs in alignment.items()
    if any(
        form in pair
        and pair[0] != pair[1]
        for pair in pairs
    )
  ]

def get_alignment_pattern_pairs_containing_form(alignment, pattern, form):
  '''TODO'''
  return [
    pair for pair in alignment[pattern]
    if form in pair
  ]


def compute_average_alignments(alignment, wordVecs):
  averages = dict()
  for pattern, pairs in alignment.items():
    # Filter pairs by those whose forms are both actually words we're learning embeddings
    # for.
    needed_pairs = [
      pair for pair in pairs
      if pair[0] in wordVecs and pair[1] in wordVecs
    ]
    # Calculate average difference between pairs.
    if len(needed_pairs) > 0:
      averages[pattern] = (
        sum(wordVecs[pair[1]] - wordVecs[pair[0]] for pair in needed_pairs)
        / len(needed_pairs)
      )

  return averages

''' Retrofit word vectors to a lexicon '''
def retrofit(wordVecs, lexicon, alignment, numIters):
  newWordVecs = deepcopy(wordVecs)
  wvVocab = set(newWordVecs.keys())
  loopVocab = wvVocab.intersection(set(lexicon.keys()))
  for it in range(numIters):
    averageAlignments = compute_average_alignments(alignment, wordVecs)
    # loop through every node also in ontology (else just use data estimate)
    for word in loopVocab:
      wordNeighbours = set(lexicon[word]).intersection(wvVocab)
      numNeighbours = len(wordNeighbours)

      wordPatterns = get_alignment_patterns_containing_form(alignment, word)
      wordPatternPairs = {
        pattern: [
          pair for pair in alignment[pattern]
          if (
              word in pair
              and pair[0] in loopVocab
              and pair[1] in loopVocab
          )
        ]
        for pattern in wordPatterns
      }
      numPairs = sum(len(pairs) for pairs in wordPatternPairs.values())

      #no neighbours, pass - use data estimate
      if numNeighbours == 0 and numPairs == 0:
        continue

      # the weight of the data estimate if the number of neighbours
      newVec = (numNeighbours + numPairs) * wordVecs[word]

      # loop over neighbours and add to new vector (currently with weight 1)
      for ppWord in wordNeighbours:
        newVec += newWordVecs[ppWord]

      # loop over patterns and add what the vector *would* be if that pattern was the only
      # thing determining it's values
      for pattern, pairs in wordPatternPairs.items():
        for base, morph in pairs:
          # If the current word is the base form of the pair, we want to target the vector
          # obtained by going backwards from the morph to its expected base.
          if word == base:
            target = newWordVecs[morph] - averageAlignments[pattern]
          # If the current word is the morph form of the pair, we want to target the
          # vector obtained by going forwards from the base to its expected morph.
          elif word == morph:
            target = newWordVecs[base] + averageAlignments[pattern]

          newVec += target

      newWordVecs[word] = newVec/(2*numNeighbours + 2*numPairs)

  return newWordVecs

if __name__=='__main__':

  parser = argparse.ArgumentParser()
  parser.add_argument("-i", "--input", type=str, default=None, help="Input word vecs")
  parser.add_argument("-l", "--lexicon", type=str, default=None, help="Lexicon file name")
  parser.add_argument("-a", "--alignment", type=str, default=None, help="Alignment index file name")
  parser.add_argument("-o", "--output", type=str, help="Output word vecs")
  parser.add_argument("-n", "--numiter", type=int, default=10, help="Num iterations")
  args = parser.parse_args()

  wordVecs = read_word_vecs(args.input)
  lexicon = read_lexicon(args.lexicon)
  alignment = read_alignment(args.alignment)
  numIter = int(args.numiter)
  outFileName = args.output

  ''' Enrich the word vectors using ppdb and print the enriched vectors '''
  print_word_vecs(retrofit(wordVecs, lexicon, alignment, numIter), outFileName)
