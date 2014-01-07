
from music21 import stream, note, chord, articulations, expressions, key, meter, bar, dynamics, repeat

def create_m21Note(nobj):
    n = note.Note(nobj.get_m21name(), quarterLength=nobj.get_quarterLength())
    n.accidental = nobj.get_m21accidental()
    n.articulations = [a() for a in nobj.get_m21articulations()]
    n.expressions = [e() for e in nobj.get_m21expressions()]
    return n
    
def extractMergedDiacritics(n1, n2):
    artic = n1.articulations
    for a in n2.articulations:
        if a not in n1.articulations:
            n1.articulations.append(a)
    n1.articulations = []
    n2.articulations = []
    
    expre = n1.expressions
    for a in n2.expressions:
        if a not in n1.expressions:
            n1.expressions.append(a)
    n1.expressions = []
    n2.expressions = []
    
    return [artic, expre]

def translateToMusic21(tree):
    part = stream.Part()
    part.append(stream.Measure()) # measure['current'] is always already contained in part
    measure = {'current' : part[-1], 'counter' : 0} # beacause measure numbers are not set automatically
                                                    # (dict as work-around for *nonlocal* statement of Python 3.*)
    repeatEnds = []
    
    def insertNewMeasure():
        part.append( stream.Measure() )
        measure['current'] = part[-1]
        measure['counter'] += 1
        measure['current'].number = measure['counter']
    
    for structure in tree:
        # (time structures)
        if isinstance(structure, Chord):
            if len(structure) > 1:
                noteList = []
                for nobj in structure:
                    n = create_m21Note(nobj)
                    noteList.append(n)
                c = chord.Chord(noteList)
                # transfer first-note and last-note diacritics to chord diacritics
                chordArticulations, chordExpressions = extractMergedDiacritics(c[0], c[-1])
                c.articulations = chordArticulations
                c.expressions = chordExpressions
                
                measure['current'].append( c )
            else:
                measure['current'].append( create_m21Note(structure[0]) )
                
        if isinstance(structure, Rest):
            measure['current'].append( note.Rest(quarterLength=structure.get_quarterLength()) )
        # (end time structures)
        
        # (signatures)
        if isinstance(structure, KeySignature):
            measure['current'].clef = structure.get_m21clef()() # instantiation
            measure['current'].insert(0.0, key.KeySignature(structure.getm21signature()) )
        
        if isinstance(structure, TimeSignature):
            measure['current'].insert(0.0, meter.TimeSignature(structure.get_m21fractionalTime()) )
        # (end signatures)
        
        # (barlines)
        if isinstance(structure, MeasureEnd):
            insertNewMeasure()
        
        if isinstance(structure, SectionEnd):
            measure['current'].append( bar.BarLine(style='double') )
            insertNewMeasure()
        
        if isinstance(structure, End):
            measure['current'].append( bar.BarLine(style='final') )
            insertNewMeasure()
        # (end barlines)
        
        # (dynamics)
        if isinstance(structure, Dynamic):
            if isinstance(measure['current'][-1], chord.Chord):
                lastChordOffset = measure['current'][-1].offset
                measure['current'].insert(lastChordOffset, dynamics.Dynamic(structure.get_m21dynamic))
            else:
                measure['current'].append( dynamics.Dynamic(structure.get_m21dynamic) )
        
        if isinstance(structure, GradualDynamic):
            if isinstance(measure['current'][-1], chord.Chord):
                lastChordOffset = measure['current'][-1].offset
                if structure.get_name() == 'crescendo':
                    measure['current'].insert(lastChordOffset, dynamics.Crescendo() )
                else:
                    measure['current'].insert(lastChordOffset, dynamics.Diminuendo() )
            else:
                if structure.get_name() == 'crescendo':
                    measure['current'].append( dynamics.Crescendo() )
                else:
                    measure['current'].append( dynamics.Diminuendo() )
        # (end dynamics)
        
        # (repeat structures)
        if isinstance(structure, RepeatFrom):
            if not isinstance(measure['current'][-1], bar.Repeat):
                insertNewMeasure()
            measure['current'].append( bar.Repeat(direction='start') )
            
        if isinstance(structure, RepeatTo):
            if len(repeatEnds) != 0: # close last repeat section
                startMeasureNo = repeatEnds.pop()
                endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part, startMeasureNo, endMeasureNo, endingNumber=endingNo, inPlace=True)
            
            measure['current'].append( bar.Repeat(direction='end', times=2) )
            insertNewMeasure()
        
        if isinstance(structure, RepeatSectionStart):
            if len(repeatEnds) != 0: # close last repeat section
                startMeasureNo = repeatEnds.pop()
                endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part, startMeasureNo, endMeasureNo, endingNumber=endingNo, inPlace=True)
            
            if len(measure['current']) == 0:
                repeatEnds.append(measure['current'].number)
            else:
                repeatEnds.append(measure['current'].number + 1)
            
        if isinstance(structure, RepeatSectionEnd):
            startMeasureNo = repeatEnds.pop()
            if len(measure['current']) == 0:
                endMeasureNo = part[-2].number
            else:
                endMeasureNo = measure['current'].number
            endingNo = structure.get_m21no()
            repeat.insertRepeatEnding(part, startMeasureNo, endMeasureNo, endingNumber=endingNo, inPlace=True)
            
        if isinstance(structure, Coda):
            measure['current'].append( repeat.Coda() )
        
        if isinstance(structure, Segno):
            measure['current'].append( repeat.Segno() )
        
        if isinstance(structure, FromTo):
            repfrom, repto = structure.get_m21parameters()
            
            if repfrom == 'D.C.':
                if repto == None:
                    measure['current'].append( repeat.DaCapo() )
                if repto == 'al Coda':
                    measure['current'].append( repeat.DaCapoAlCoda() )
                if repto == 'al Fine':
                    measure['current'].append( repeat.DaCapoAlFine() )
            if repfrom == 'D.S.':
                if repto == None:
                    measure['current'].append( repeat.DalSegno() )
                if repto == 'al Coda':
                    measure['current'].append( repeat.DalSegnoAlCoda() )
                if repto == 'al Fine':
                    measure['current'].append( repeat.DalSegnoAlFine() )
        # (end repeat structures)
            
    # Clean-up
    if type(part[-1]) is stream.Measure and len(part[-1]) == 0:
        silent = part.pop(-1)
        
    return part
    

def writeStream(m21stream, format='midi', wrtpath=None):
    """
    Write out Music21 stream in a given format. If wrtpath is not specified
    the file is written in the current working directory (as 'untitled.ext')
    
    The possible output formats are
        musicxml lily(pond) midi
    """
    import os
    from music21.common import findFormat
    
    fmt, ext = findFormat(format)
    
    if not wrtpath:
        wrtpath = os.path.join(os.getcwd(), 'untitled' + ext)
    if os.path.isdir(wrtpath):
        wrtpath = os.path.join(wrtpath, 'untitled' + ext)
        
    m21stream.write(format, wrtpath)
    

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) >= 2:
        t = parse(sys.argv[1])
        s = translateToMusic21(t)
        if len(sys.argv) == 2:
            writeStream(s)
        if len(sys.argv) == 3:
            writeStream(s, format=sys.argv[2])
    else:
        print """Usage:
    $ python parser.py [string] [format]\n
Output path is current working directory.
Test-strings:
    '_----~34 a d g, sfh g j,'  Signatures & chords
    ', a a- a--, g g= g==,'     Accidentals
    ', a D g; d F d:'           Repetition markings"""
        
        
        
              
            