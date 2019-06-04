if __name__ == '__main__':
    import sys, os

    if len(sys.argv) >= 2:
        from language.syntax import parse
        import translator

        # input path
        filepath = sys.argv[1]
        filedir = os.path.dirname(os.path.abspath(filepath))
        base = os.path.basename(filepath)
        filename = os.path.splitext(base)[0]

        # extension
        fmt = "musicxml"
        if len(sys.argv) == 3:
            if sys.argv[2] not in ["musicxml", "midi"]:
                raise SyntaxError(sys.argv[2] + " is not a valid format.")
            fmt = sys.argv[2]
        fileext = {"musicxml" : ".xml", "xml" : ".xml", "midi" : ".midi", "mid" : ".midi"}

        # output path
        wrtpath = os.path.join(filedir, filename)
        nakedpath = wrtpath
        i = 0
        while os.path.isfile(nakedpath + fileext[fmt]):
            i += 1
            nakedpath = wrtpath + ("%02d" % i)
            if i > 99:
                break
        wrtpath = nakedpath + fileext[fmt]

        # write
        with open(filepath, "rt") as fin:
            tree = parse(fin.read())
            score = translator.translateToMusic21(tree)
            if len(sys.argv) == 2:
                translator.writeStream(score, format='musicxml', wrtpath=wrtpath)
            if len(sys.argv) == 3:
                translator.writeStream(score, format=sys.argv[2], wrtpath=wrtpath)

    else:
        print("Usage:\n\t$ python rtf2xml.py [path] [format]\nOutput path is current working directory. Available formats are 'musicxml' (default) and 'midi'.")
