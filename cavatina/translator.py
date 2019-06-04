from music21 import stream, note, chord, key, meter, bar, dynamics, tie, repeat, spanner, layout, metadata, tempo, \
    instrument

from .language.structures import Note, Chord, Rest, KeySignature, Dynamic, BoldSystemicBarline, TimeSignature, MeasureEnd, RepeatFrom, RepeatTo, End, SystemicBarline, SectionEnd, GradualDynamic, RepeatSectionStart, RepeatSectionEnd, Coda, Segno, FromTo, OctavationStart, OctavationEnd, GrandStaff, Newline

def create_m21Note(nobj):
    n = note.Note(nobj.get_m21name(), quarterLength=nobj.get_quarterLength())
    n.accidental = nobj.get_m21accidental()
    n.articulations = [a() for a in nobj.get_m21articulations()]
    n.expressions = [e() for e in nobj.get_m21expressions()]
    if nobj.is_tied():
        n.tie = tie.Tie("start")
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


def translateToMusic21(tree, preserveStemDirection=False):
    score = stream.Score()

    score.insert(metadata.Metadata())
    # score.metadata.title = 'Untitled'
    # score.metadata.composer = 'Unknown Composer'

    score.append(stream.Part())
    part = score[-1]
    part.append(stream.Measure()
                )  # measure['current'] is always already contained in part
    measure = {
        'current': part[-1],
        'counter': 0
    }  # because measure numbers are not set automatically
    # (dict as work-around for *nonlocal* statement in Python 3)
    repeatEnds = []
    makeVoices = []  # for multi-voice chords
    lastKeySign = {
        0: None,
        1: None,
        2: None,
        3: None,
        4: None
    }  # part number : int
    lastClef = {0: None, 1: None, 2: None, 3: None, 4: None}
    lastTimeSign = {0: None, 1: None, 2: None, 3: None, 4: None}

    # states
    octavationSwitch = False
    catchPartitioning = False  # watch-state triggered by a Newline

    def insertNewMeasure():
        part.append(stream.Measure())
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
                    if preserveStemDirection:
                        n.stemDirection = nobj.stem_direction
                    noteList.append(n)

                # Trim chord into chord voices
                chordVoices = [[noteList[0]]]
                currentLength = noteList[0].quarterLength
                currentVoice = chordVoices[0]

                for n in noteList[1:]:
                    if n.quarterLength != currentLength:
                        chordVoices.append([n])
                        currentLength = n.quarterLength
                        currentVoice = chordVoices[-1]
                    else:
                        currentVoice.append(n)

                # Make chords
                for nlist in chordVoices:
                    c = chord.Chord(nlist)
                    chordArticulations, chordExpressions = extractMergedDiacritics(
                        c[0], c[-1]
                    )  # transfer first-note and last-note diacritics to chord diacritics
                    c.articulations = chordArticulations  # some articulations are not yet translated from music21 into Lilypond (staccato, tenuto, etc.)
                    c.expressions = chordExpressions  # idem. (mordent, turn, trill, etc.)
                    if nlist == chordVoices[0]:
                        measure['current'].append(c)
                        chordOffset = measure['current'][-1].offset
                    else:
                        measure['current'].insert(chordOffset, c)  # overlap

                if len(chordVoices) > 1:  # if overlap
                    makeVoices.append((part.id, measure['current'].number
                                       ))  # remember overlap locations

            else:
                measure['current'].append(create_m21Note(structure[0]))

            # Beams
            if structure.beamToPrevious:
                try:
                    measure['current'][-2].beams.fill('eighth', type='start')
                    measure['current'][-1].beams.fill('eighth', type='stop')
                except stream.StreamException:
                    pass  # TODO: handle StreamException

            # Ottava
            if octavationSwitch:
                measure['current'][-1].transpose('p8', inPlace=True)
                ottava.addSpannedElements(measure['current'][-1])

            continue

        if isinstance(structure, Rest):
            measure['current'].append(
                note.Rest(quarterLength=structure.get_quarterLength()))
            continue
        # (end time structures)

        # (signatures)
        if isinstance(structure, KeySignature):
            if catchPartitioning:
                # Return to first part
                part = score[1]  # score[0] is the metadata object
                measure['counter'] = part[-1].number
                insertNewMeasure()
                catchPartitioning = False

            i = score.index(part)
            newClef = structure.get_m21clef()()
            newKeySign = structure.getm21signature()

            if newKeySign != lastKeySign[i] or newClef.sign != lastClef[i]:
                lastKeySign[i] = newKeySign
                lastClef[i] = newClef.sign
                measure['current'].clef = newClef  # instantiation
                measure['current'].insert(0.0, key.KeySignature(newKeySign))
            continue

        if isinstance(structure, TimeSignature):
            newTimeSignature = meter.TimeSignature(
                structure.get_m21fractionalTime())
            i = score.index(part)
            if newTimeSignature.ratioString != lastTimeSign[i]:
                lastTimeSign[i] = newTimeSignature.ratioString
                measure['current'].insert(0.0, newTimeSignature)
            continue
        # (end signatures)

        # (barlines)
        if isinstance(structure, MeasureEnd):
            if catchPartitioning and not isinstance(structure,
                                                    SystemicBarline):
                # Return to first part
                part = score[1]  # score[0] is the metadata object
                measure['counter'] = part[-1].number
                insertNewMeasure()
                catchPartitioning = False

            elif len(measure['current']) > 0:
                insertNewMeasure()

        if isinstance(structure, SectionEnd):
            measure['current'].append(bar.Barline(style='double'))
            insertNewMeasure()
            continue

        if isinstance(structure, End):
            if len(repeatEnds) != 0:  # close last repeat section
                startMeasureNo, endingNo = repeatEnds.pop()
                endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part,
                                          startMeasureNo,
                                          endMeasureNo,
                                          endingNumber=endingNo,
                                          inPlace=True)

            measure['current'].append(bar.Barline(style='final'))
            insertNewMeasure()
            continue
        # (end barlines)

        # (dynamics)
        if isinstance(structure, Dynamic):
            if len(measure['current']) > 0 and isinstance(
                    measure['current'][-1], chord.Chord) or isinstance(
                        measure['current'][-1], note.Note):
                lastChordOffset = measure['current'][-1].offset
                measure['current'].insert(
                    lastChordOffset,
                    dynamics.Dynamic(structure.get_m21dynamic()))
            else:
                measure['current'].append(
                    dynamics.Dynamic(structure.get_m21dynamic()))
            continue

        if isinstance(structure, GradualDynamic):
            if len(measure['current']) > 0 and isinstance(
                    measure['current'][-1], chord.Chord):
                lastChordOffset = measure['current'][-1].offset
                if structure.get_name() == 'crescendo':
                    measure['current'].insert(lastChordOffset,
                                              dynamics.Crescendo())
                else:
                    measure['current'].insert(lastChordOffset,
                                              dynamics.Diminuendo())
            else:
                if structure.get_name() == 'crescendo':
                    measure['current'].append(dynamics.Crescendo())
                else:
                    measure['current'].append(dynamics.Diminuendo())
            continue
        # (end dynamics)

        # (repeat structures)
        if isinstance(structure, RepeatFrom):
            if len(measure['current']) > 0 and not isinstance(
                    measure['current'][-1], bar.Repeat):
                insertNewMeasure()
            measure['current'].leftBarline = bar.Repeat(direction='start')
            continue

        if isinstance(structure, RepeatTo):
            if len(repeatEnds) != 0:  # close last repeat section
                startMeasureNo, endingNo = repeatEnds.pop()
                endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part,
                                          startMeasureNo,
                                          endMeasureNo,
                                          endingNumber=endingNo,
                                          inPlace=True)

            measure['current'].rightBarline = bar.Repeat(direction='end')
            insertNewMeasure()
            continue

        if isinstance(structure, RepeatSectionStart):
            if len(repeatEnds) != 0:  # close last repeat section
                startMeasureNo, endingNo = repeatEnds.pop()
                if len(measure['current']) == 0:
                    endMeasureNo = measure['current'].number - 1
                else:
                    endMeasureNo = measure['current'].number
                repeat.insertRepeatEnding(part,
                                          startMeasureNo,
                                          endMeasureNo,
                                          endingNumber=endingNo,
                                          inPlace=True)

            endingNo = structure.get_m21no()
            if len(measure['current']) == 0:
                repeatEnds.append([measure['current'].number, endingNo])
            else:
                repeatEnds.append([measure['current'].number + 1, endingNo])
            continue

        if isinstance(structure, RepeatSectionEnd):
            startMeasureNo, endingNo = repeatEnds.pop()
            if len(measure['current']) == 0:
                endMeasureNo = part[-2].number
            else:
                endMeasureNo = measure['current'].number
            repeat.insertRepeatEnding(part,
                                      startMeasureNo,
                                      endMeasureNo,
                                      endingNumber=endingNo,
                                      inPlace=True)
            continue

        if isinstance(structure, Coda):
            measure['current'].append(repeat.Coda())
            continue

        if isinstance(structure, Segno):
            measure['current'].append(repeat.Segno())
            continue

        if isinstance(structure, FromTo):
            repfrom, repto = structure.get_m21parameters()

            if repfrom == 'D.C.':
                if repto == None:
                    measure['current'].append(repeat.DaCapo())
                if repto == 'al Coda':
                    measure['current'].append(repeat.DaCapoAlCoda())
                if repto == 'al Fine':
                    measure['current'].append(repeat.DaCapoAlFine())
            if repfrom == 'D.S.':
                if repto == None:
                    measure['current'].append(repeat.DalSegno())
                if repto == 'al Coda':
                    measure['current'].append(repeat.DalSegnoAlCoda())
                if repto == 'al Fine':
                    measure['current'].append(repeat.DalSegnoAlFine())
            continue
        # (end repeat structures)

        # (ottava)
        if isinstance(structure, OctavationStart):
            otp = structure.octaveTranspositions
            if otp == 0 and len(measure['current']) > 0:  # single octavation
                measure['current'][-1].transpose('p8', inPlace=True)
                ottava = spanner.Ottava(measure['current'][-1], type='8va')
                measure['current'].append(ottava)
            elif otp == 1:  # spanning octavation (1x)
                ottava = spanner.Ottava(type='8va')
                octavationSwitch = True
            elif otp == 2:  # spanning octavation (2x)
                ottava = spanner.Ottava(type='15ma')
                octavationSwitch = True
            continue

        if isinstance(structure, OctavationEnd):
            part.insert(0.0, ottava)
            octavationSwitch = False
            continue
        # (end ottava)

        # (sustain pedal)
        #
        # A corresponding music21.spanner object is not yet implemented in the music21 library.
        # TODO: fork cuthbertLab/music21 and implement e.g. `music21.spanner.Pedal`
        #
        # if isinstance(structure, PedalDown):
        # if isinstance(structure, PedalUp):
        #
        # (end sustain pedal)

        # (grand staff)
        if isinstance(structure, GrandStaff) or isinstance(
                structure, SystemicBarline):
            if catchPartitioning:
                if part == score.parts[-1]:  # part is last part
                    # Create new part and re-initialize
                    part = stream.Part()
                    score.append(part)
                    part.offset = 0.0
                    measure['counter'] = -1
                    insertNewMeasure()

                    if isinstance(structure, GrandStaff):
                        p1 = score.parts[-2]
                        p2 = score.parts[-1]  # = part
                        staffGroup = layout.StaffGroup([p1, p2],
                                                       symbol='brace')
                        score.insert(0.0, staffGroup)

                    if isinstance(structure, SystemicBarline):
                        SystBarline = score.getElementsByClass(
                            layout.StaffGroup)[0] if len(
                                score.getElementsByClass(
                                    layout.StaffGroup)) > 0 else None
                        if not SystBarline:
                            p1 = score.parts[-2]
                            p2 = score.parts[-1]  # = part
                            staffGroup = layout.StaffGroup([p1, p2],
                                                           symbol='line')
                            score.insert(0.0, staffGroup)
                        else:
                            SystBarline.addSpannedElements(part)

                else:  # next parts already exist
                    part = part.next('Part')
                    measure['counter'] = part[-1].number if isinstance(part[-1], stream.Measure) else part[-1].measureNumber
                    insertNewMeasure()

                catchPartitioning = False
                continue
        # (end grand staff)

        # New line
        if isinstance(structure, Newline):
            # Clean-up
            if type(part[-1]) is stream.Measure and len(part[-1]) == 0:
                part.remove(part[-1])  # measure['current']
            catchPartitioning = True  # trigger watch-state
            continue

    # Clean-up
    if type(part[-1]) is stream.Measure and len(part[-1]) == 0:
        part.remove(part[-1])  # measure['current']

    # Separate overlaps
    for partId, measureNo in makeVoices:
        p = score.getElementById(partId)
        p[measureNo].makeVoices(
        )  # ugly results when durations don't fit, automatically generated rests

    # Automatic beams
    # if autoBeams:
    #     for p in score.parts: # echo TimeSignature declarations
    #         ts = p[0].getElementsByClass(meter.TimeSignature)[0] if len(p[0].getElementsByClass(meter.TimeSignature)) > 0 else meter.TimeSignature('4/4')
    #         for m in p:
    #             if len(m.getElementsByClass(meter.TimeSignature)) > 0:
    #                 ts = m.getElementsByClass(meter.TimeSignature)[0]
    #             else:
    #                 m.timeSignature = ts
    #
    #     for p in score.parts: # make auto-beams
    #         p.makeBeams(inPlace=True)

    return score


def setMetadata(m21stream,
                scoreTitle="Untitled",
                scoreComposer="Unknown Composer",
                scoreTempo=None,
                scoreInstruments=None,
                midiPrograms=False):
    """
    scoreTitle: str
    scoreComposer: str
    scoreTempo: int
    scoreInstruments: list[ str ]
    midiPrograms: bool
    """
    if not m21stream.metadata:
        m21stream.insert(0.0, metadata.Metadata())
    if scoreTitle:
        m21stream.metadata.title = scoreTitle
    else:
        m21stream.metadata.title = "Untitled"
    if scoreComposer:
        m21stream.metadata.composer = scoreComposer
    else:
        m21stream.metadata.composer = "Unknown Composer"
    if scoreTempo:
        m21stream.insert(0, tempo.MetronomeMark(number=scoreTempo))
    if scoreInstruments:
        if len(scoreInstruments) == 1:
            for p in m21stream.parts:
                if midiPrograms:
                    p.insert(
                        0,
                        instrument.instrumentFromMidiProgram(
                            scoreInstruments[0]))
                else:
                    p.insert(0, instrument.fromString(scoreInstruments[0]))
        else:
            parts = m21stream.parts
            for n, i in enumerate(scoreInstruments):
                if midiPrograms:
                    parts[n].insert(0, instrument.instrumentFromMidiProgram(i))
                else:
                    parts[n].insert(0, instrument.fromString(i))


def writeStream(m21stream,
                format='midi',
                wrtpath=None,
                scoreTitle=None,
                scoreComposer=None,
                scoreTempo=None,
                scoreInstruments=None):
    """
    scoreTitle: str
    scoreComposer: str
    scoreTempo: int
    scoreInstruments: list[ str ]

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

    # Part writing (app.py: MyFrame.getOffsetScore)
    if isinstance(m21stream, stream.Part):
        import copy
        score = stream.Score()
        score.append(copy.deepcopy(m21stream))
        m21stream = score

    # Metadata
    setMetadata(m21stream,
                scoreTitle=scoreTitle,
                scoreComposer=scoreComposer,
                scoreTempo=scoreTempo,
                scoreInstruments=scoreInstruments,
                midiPrograms=False)

    m21stream.write(format, wrtpath)


if __name__ == '__main__':
    import sys
    from .language.syntax import parse

    if len(sys.argv) >= 2:
        t = parse(sys.argv[1])
        s = translateToMusic21(t)
        if len(sys.argv) == 2:
            writeStream(s)
        if len(sys.argv) == 3:
            writeStream(s, format=sys.argv[2])
    else:
        print(
            "Usage:\n\t$ python translator.py [string] [format]\nOutput path is current working directory."
        )
