# write.py -- for testing purposes
from os.path import dirname, abspath, join

from cavatina.lexer import parse
import cavatina.translator as translator

def writeFiles(filename, outfilename, filedir=None):
    """
    Input file format may be .txt or .rtf
    """
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
    import sys
    sys.path.append(dirname(abspath(__file__)))
    
    if len(sys.argv) > 1:
        if len(sys.argv) == 2 and sys.argv[1] == '-h':
            print "Usage:\tpython write.py [input file path] [output directory]"
        else:
            filename = sys.argv[1]
            if len(sys.argv) == 3:
                filedir = sys.argv[2]
            else:
                filedir = None
            outfilename = "out.txt"
            writeFiles(filename, outfilename, filedir)
    else:
        print "Usage:\tpython write.py [input file path] [output directory]"
        