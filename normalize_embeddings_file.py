#!/usr/bin/env python3

import os
import sys

embeddings_path = sys.argv[1]
temp_path = '.' + sys.argv[1] + '.tmp'
dim = int(sys.argv[2])

with (
        open(embeddings_path, 'r') as embeddings_file,
        open(temp_path, 'w') as temp_file,
):
    for line in embeddings_file.readlines():
        split = line.split()
        temp_file.write("_".join(split[:-dim]))
        temp_file.write(" ")
        temp_file.write(" ".join(split[-dim:]))
        temp_file.write("\n")

os.rename(temp_path, embeddings_path)
