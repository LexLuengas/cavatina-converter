import fileinput
from os.path import join

file_names = ['semantics.py', 'symbols.py', 'structures.py', 'syntax.py']
source_dir = 'src'

dir_collection = [join(source_dir, n) for n in file_names]

with open('parser.py', 'w') as fout:
    for line in fileinput.input(dir_collection):
        fout.write(line)