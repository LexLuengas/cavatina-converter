
from parser import *
from music21 import stream, note, chord, articulations, expressions, key, meter, bar, dynamics, repeat, spanner, layout

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
    score = stream.Score()
    score.append(stream.Part())
    part = score[-1]
    part.append(stream.Measure()) # measure['current'] is always already contained in part
    measure = {'current': part[-1], 'counter': 0} # beacause measure numbers are not set automatically
                                                  # (dict as work-around for *nonlocal* statement of Python 3.*)
    repeatEnds = []
    octavationSwitch = False
    catchPartitioning = False # watch-state triggered by a Newline
    
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
                c.articulations = chordArticulations # some articulations are not yet translated from music21 into Lilypond (staccato, tenuto, etc.)
                c.expressions = chordExpressions # idem. (mordent, turn, trill, etc.)
                
                measure['current'].append( c )
            else:
                measure['current'].append( create_m21Note(structure[0]) )
            if octavationSwitch:
                measure['current'][-1].transpose('p8', inPlace=True)
                ottava.addSpannedElements(measure['current'][-1])
                
        if isinstance(structure, Rest):
            measure['current'].append( note.Rest(quarterLength=structure.get_quarterLength()) )
        # (end time structures)
        
        # (signatures)
        if isinstance(structure, KeySignature):
            if catchPartitioning:
                part = score[0]
                part.append(stream.Measure())
                measure['current'] = part[-1]
            
            measure['current'].clef = structure.get_m21clef()() # instantiation
            measure['current'].insert(0.0, key.KeySignature(structure.getm21signature()) )
        
        if isinstance(structure, TimeSignature):
            measure['current'].insert(0.0, meter.TimeSignature(structure.get_m21fractionalTime()) )
        # (end signatures)
        
        # (barlines)
        if isinstance(structure, MeasureEnd):
            if catchPartitioning:
                part = score[0]
                part.append(stream.Measure())
                measure['current'] = part[-1]
                
            if len(measure['current']) > 0:
                insertNewMeasure()
        
        if isinstance(structure, SectionEnd):
            measure['current'].append( bar.Barline(style='double') )
            insertNewMeasure()
        
        if isinstance(structure, End):
            measure['current'].append( bar.Barline(style='final') )
            insertNewMeasure()
        # (end barlines)
        
        # (dynamics)
        if isinstance(structure, Dynamic):
            if isinstance(measure['current'][-1], chord.Chord) or isinstance(measure['current'][-1], note.Note):
                lastChordOffset = measure['current'][-1].offset
                measure['current'].insert(lastChordOffset, dynamics.Dynamic(structure.get_m21dynamic()))
            else:
                measure['current'].append( dynamics.Dynamic(structure.get_m21dynamic()) )
        
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
            measure['current'].leftBarline = bar.Repeat(direction='start')
            
        if isinstance(structure, RepeatTo):
            if len(repeatEnds) != 0: # close last repeat section
                startMeasureNo, endingNo = repeatEnds.pop()
                endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part, startMeasureNo, endMeasureNo, endingNumber=endingNo, inPlace=True)
            
            measure['current'].rightBarline = bar.Repeat(direction='end')
            insertNewMeasure()
        
        if isinstance(structure, RepeatSectionStart):
            if len(repeatEnds) != 0: # close last repeat section
                startMeasureNo, endingNo = repeatEnds.pop()
                if len(measure['current']) == 0:
                    endMeasureNo = measure['current'].number - 1
                else:
                    endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part, startMeasureNo, endMeasureNo, endingNumber=endingNo, inPlace=True)
            
            endingNo = structure.get_m21no()
            if len(measure['current']) == 0:
                repeatEnds.append([measure['current'].number, endingNo])
            else:
                repeatEnds.append([measure['current'].number + 1, endingNo])
            
        if isinstance(structure, RepeatSectionEnd):
            startMeasureNo, endingNo = repeatEnds.pop()
            if len(measure['current']) == 0:
                endMeasureNo = part[-2].number
            else:
                endMeasureNo = measure['current'].number
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
        
        #(ottava)
        if isinstance(structure, OctavationStart):
            otp = structure.octaveTranspositions
            if otp == 0: # single octavation
                measure['current'][-1].transpose('p8', inPlace=True)
                ottava = spanner.Ottava(measure['current'][-1], type='8va')
                measure['current'].append(ottava)
            elif otp == 1: # spanning octavation (1x)
                ottava = spanner.Ottava(type='8va')
                octavationSwitch = True
            elif otp == 2: # spanning octavation (2x)
                ottava = spanner.Ottava(type='15ma')
                octavationSwitch = True
            
        if isinstance(structure, OctavationEnd):
            part.insert(0.0, ottava)
            octavationSwitch = False
        #(end ottava)
        
        #(sustain pedal)
        #
        # A corresponding music21.spanner object is not yet implemented in the music21 library.
        # TODO: pull cuthbertLab/music21 and implement music21.spanner.Pedal
        #
        # if isinstance(structure, PedalDown):
        # if isinstance(structure, PedalUp):
        #
        #(end sustain pedal)
        
        #(grand staff)
        if isinstance(structure, GrandStaff) or isinstance(structure, SystemicBarline):
            if catchPartitioning:
                if part == score[-1]: # part is last part
                    # Re-initialize
                    part = stream.Part()
                    score.insert(0.0, part)
                    part.append(stream.Measure())
                    measure = {'current': part[-1], 'counter': 0}
                    
                    if isinstance(structure, GrandStaff):
                        p1 = score[-2]
                        p2 = score[-1] # = part
                        staffGroup = layout.StaffGroup([p1, p2], symbol='brace')
                        score.insert(0.0, staffGroup)
                        
                    if isinstance(structure, SystemicBarline):
                        partList = [p for p in score.parts]
                        staffGroup = layout.StaffGroup(partList, symbol='bracket')
                        score.insert(0.0, staffGroup)
                        
                else: # next parts already exist
                    part = part.next()
                    part.append(stream.Measure())
                    measure['current'] = part[-1]
                    
                catchPartitioning = False
        #(end grand staff)
        
        # New line
        if isinstance(structure, Newline):
            catchPartitioning = True # trigger watch-state
            
    # Clean-up
    if type(part[-1]) is stream.Measure and len(part[-1]) == 0:
        part.remove(part[-1]) # measure['current']
        
    return score
    

def writeStream(m21stream, format='midi', wrtpath=None):
    """
    Write out Music21 stream in a given format. If wrtpath is not specified
    the file is written in the current working directory (as 'untitled.ext'),
    or if wrtpath is a directory, 'untitled.ext' files are written there.
    
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
        print "Usage:\n\t$ python parser.py [string] [format]\nOutput path is current working directory."
