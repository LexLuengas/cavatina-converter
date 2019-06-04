from os.path import dirname, abspath, join

from ..language.syntax import parse
from .. import translator

def writeFiles(filename, outfilename, filedir=None, outputFormat='text'):
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
        translator.writeStream(score, format=outputFormat, wrtpath=filedir)


if __name__ == "__main__":
    import sys, os
    sys.path.append(dirname(abspath(__file__)))

    if len(sys.argv) > 1:
        if len(sys.argv) == 2 and sys.argv[1] == '-h':
            print("Usage:\tpython write.py [input file path] [output directory]")
        else:
            filename = sys.argv[1]
            if len(sys.argv) == 3:
                filedir = sys.argv[2]
            else:
                # Output to same directory as input file
                filedir = dirname(sys.argv[1]) 
            outfilename = os.path.splitext(sys.argv[1])[0] + "-out.txt"
            writeFiles(filename, outfilename, filedir)
    else:
        print("Usage:\tpython write.py [input file path] [output directory]")
