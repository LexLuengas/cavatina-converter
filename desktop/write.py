import sys
from os.path import dirname, abspath, join
sys.path.append(dirname(abspath(__file__)))

from parser import *
import translateToMusic21 as translator

def writeFiles(filename, outfilename, filedir=None):
    if filedir:
        filename = join(filedir, filename)
        outfilename = join(filedir, outfilename)
    
    with open(outfilename, "wt") as fout:
        with open(filename, "rt") as fin:
            tree = parse(fin.read())
            fout.write( '\n'.join([str(n) for n in tree]) )
            
    with open(filename, "rt") as fin:
        tree = parse(fin.read())
        score = translator.translateToMusic21(tree)
        translator.writeStream(score, format='text', wrtpath=filedir)
        translator.writeStream(score, format='midi', wrtpath=filedir)
        translator.writeStream(score, format='musicxml', wrtpath=filedir)
            

if __name__ == "__main__":
    filename = "in.txt"
    outfilename = "out.txt"
    writeFiles(filename, outfilename, './io')