if __name__ == '__main__':
    import sys, os

    if len(sys.argv) >= 2:
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
                
        from lexer import parse
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
                raise Exception
            fmt = sys.argv[2]
        fileext = {"musicxml" : ".xml", "xml" : ".xml", "midi" : ".midi", "mid" : ".midi"}
        
        # output path
        wrtpath = os.path.join(filedir, filename + fileext[fmt])
        
        # write
        with open(filepath, "rt") as fin:
            tree = parse(fin.read())
            score = translator.translateToMusic21(tree)
            if len(sys.argv) == 2:
                translator.writeStream(score, format='musicxml', wrtpath=wrtpath)
            if len(sys.argv) == 3:
                translator.writeStream(score, format=sys.argv[2], wrtpath=wrtpath)
    
    else:
        print "Usage:\n\t$ python rtf2xml.py [path] [format]\nOutput path is current working directory."