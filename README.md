# Retrofitting
Based on work by Manaal Faruqui, manaalfar@gmail.com

This tool is used to post-process word vectors to incorporate
knowledge from semantic lexicons. As shown in Faruqui et al, 2015
these word vectors are generally better in performance on semantic
tasks than the original word vectors. This tool can be used for
word vectors obtained from any vector training model.

Additionally, this version of the tool takes the vector difference between word pairs of shared morphological relations into account. For example, "run" and "runs" share a relationship with "sing" and "sings," so the tool will attempt to assign embeddings for those words such that the difference between the vector representations of "run" and "runs" is similar to the difference between the vector representations of "sing" and "sings."

### Requirements

1. Python 3.8
2. Numpy

### Data you need

1. Word vector file
2. Lexicon file (provided here)

Each vector file should have one word vector per line as follows (space delimited):-

```the -1.0 2.4 -0.3 ...```

### Generating morphology data

Morphology relation / transformation data can be generated using the mkindex_catvar.py script. Example usage:

```python mkindex_catvar.py -o catvar.json```

You do not need to separately obtain CATVAR, it is included as a submodule of this project.

### Running the program

```python retrofit.py -i word_vec_file -l lexicon_file -t morphology_file -n num_iter -o out_vec_file```

```python retrofit.py -i sample_vec.txt -l lexicons/ppdb-xl.txt -t catvar.json -n 10 -o out_vec.txt```

```python retrofit.py -i word_vec_file -l lexicon_file -n num_iter -o out_vec_file```

```python retrofit.py -i sample_vec.txt -l lexicons/ppdb-xl.txt -n 10 -o out_vec.txt```

where, 'n' is an integer which specifies the number of iterations for which the
optimization is to be performed.  Usually n = 10 gives reasonable results.

Either `-l` or `-t` may be omitted, but not both.

### Output
File: ```out_vec.txt```

which are your new retrofitted and (hopefully) improved word vectors, enjoy !

### Reference

Main paper to be cited
```
@InProceedings{faruqui:2015:NAACL,
  author    = {Faruqui, Manaal and Dodge, Jesse and Jauhar, Sujay K.  and  Dyer, Chris and Hovy, Eduard and Smith, Noah A.},
  title     = {Retrofitting Word Vectors to Semantic Lexicons},
  booktitle = {Proceedings of NAACL},
  year      = {2015},
}
```

If you are using PPDB (Ganitkevitch et al, 2013), WordNet (Miller, 1995) or FrameNet (Baker et al, 1998) for enrichment please cite the corresponding papers.

