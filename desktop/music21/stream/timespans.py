# -*- coding: utf-8 -*-
#------------------------------------------------------------------------------
# Name:         timespanStream.py
# Purpose:      Tools for grouping notes and chords into a searchable tree
#               organized by start and stop offsets
#
# Authors:      Josiah Wolf Oberholtzer
#
# Copyright:    Copyright © 2013-14 Michael Scott Cuthbert and the music21
#               Project
# License:      LGPL, see license.txt
#------------------------------------------------------------------------------
'''
Tools for grouping notes and chords into a searchable tree
organized by start and stop offsets.

This is a lower-level tool that for now at least normal music21
users won't need to worry about.
'''


import bisect
import collections
import copy
import random
import unittest
from music21 import chord
from music21 import instrument
from music21 import note
from music21 import pitch
from music21 import tie
from music21 import exceptions21


#------------------------------------------------------------------------------


def makeElement(verticality, quarterLength):
    r'''
    Makes an element from a verticality and quarterLength.
    '''
    if verticality.pitchSet:
        element = chord.Chord(sorted(verticality.pitchSet))
        startElements = [x.element for x in
            verticality.startTimespans]
        ties = [x.tie for x in startElements if x.tie is not None]
        if any(x.type == 'start' for x in ties):
            element.tie = tie.Tie('start')
        elif any(x.type == 'continue' for x in ties):
            element.tie = tie.Tie('continue')
    else:
        element = note.Rest()
    element.duration.quarterLength = quarterLength
    return element


def recurseStream(
    inputStream,
    currentParentage=None,
    ):
    r'''
    Recurses through `inputStream`, constructs ElementTimespans for each
    non-stream pitched element found, and returns all constructed 
    ElementTimespans.
    '''
    from music21 import stream
    if currentParentage is None:
        currentParentage = (inputStream,)
    result = []
    for element in inputStream:
        if isinstance(element, stream.Stream):
            localParentage = currentParentage + (element,)
            subresult = recurseStream(element, localParentage)
            result.extend(subresult)
            continue
        if not isinstance(element, (
            note.Note,
            chord.Chord,
            )):
            continue
        if isinstance(currentParentage[-1], stream.Measure) and \
            1 < len(currentParentage):
            measure = currentParentage[-1]
            measureParent = currentParentage[-2]
            measureStartOffset = measure.getOffsetBySite(measureParent)
            measureStopOffset = measureStartOffset + \
                measure.duration.quarterLength
        else:
            measureStartOffset = None
            measureStopOffset = None
        startOffset = element.getOffsetBySite(currentParentage[-1])
        if measureStartOffset is not None:
            startOffset = measureStartOffset + startOffset
        stopOffset = startOffset + element.quarterLength
        elementTimespan = ElementTimespan(
            element=element,
            measureStartOffset=measureStartOffset,
            measureStopOffset=measureStopOffset,
            parentage=tuple(reversed(currentParentage)),
            startOffset=startOffset,
            stopOffset=stopOffset,
            )
        result.append(elementTimespan)
    return result


def streamToTimespanCollection(inputStream):
    r'''
    Recurses through a score and constructs a timespan collection.

    ::

        >>> score = corpus.parse('bwv66.6')
        >>> tree = stream.timespans.streamToTimespanCollection(score)
        >>> for x in tree[:5]:
        ...     x
        ...
        <ElementTimespan 0.0:0.5 <music21.note.Note C#>>
        <ElementTimespan 0.0:0.5 <music21.note.Note A>>
        <ElementTimespan 0.0:0.5 <music21.note.Note A>>
        <ElementTimespan 0.0:1.0 <music21.note.Note E>>
        <ElementTimespan 0.5:1.0 <music21.note.Note B>>

    '''
    elementTimespans = recurseStream(inputStream)
    tree = TimespanCollection()
    tree.insert(elementTimespans)
    return tree


#------------------------------------------------------------------------------


class Timespan(object):
    def __init__(self, startOffset, stopOffset):
        if startOffset < stopOffset:
            self.startOffset = startOffset
            self.stopOffset = stopOffset
        else:
            self.startOffset = stopOffset
            self.stopOffset = startOffset

    def __eq__(self, expr):
        if type(self) is type(expr):
            if self.startOffset == expr.startOffset:
                if self.stopOffset == expr.stopOffset:
                    return True
        return False

    def __repr__(self):
        return '<{} {} {}>'.format(
            type(self).__name__,
            self.startOffset,
            self.stopOffset,
            )

#------------------------------------------------------------------------------


class ElementTimespan(object):
    r'''
    A span of time anchored to an element in a score.  The span of time may
    be the same length as the element in the score.  It may be shorter (a
    "slice" of an element) or it may be longer (in the case of a timespan
    that is anchored to a single element but extends over rests or other
    notes following a note)

    ElementTimespans give
    information about an element (such as a Note).  It knows
    its absolute position with respect to
    the element passed into TimespanCollection.  It contains information
    about what measure it's in, what part it's in, etc.

    Example, getting a passing tone from a known location from a Bach chorale.

    First we create an Offset tree:

    ::

        >>> score = corpus.parse('bwv66.6')
        >>> tree = stream.timespans.TimespanCollection(score)
        >>> tree
        <music21.stream.timespans.TimespanCollection object at 0x...>

    Then get the verticality from offset 6.5, which is beat two-and-a-half of
    measure 2 (the piece is in 4/4 with a quarter-note pickup)

    ::

        >>> verticality = tree.getVerticalityAt(6.5)
        >>> verticality
        <Verticality 6.5 {E3 D4 G#4 B4}>

    There are four elementTimespans in the verticality -- each representing
    a note.  The notes are arranged from lowest to highest.


    We can find all the elementTimespans that start exactly at 6.5. There's
    one.

    ::

        >>> verticality.startTimespans
        (<ElementTimespan 6.5:7.0 <music21.note.Note D>>,)
        >>> elementTimespan = verticality.startTimespans[0]
        >>> elementTimespan
        <ElementTimespan 6.5:7.0 <music21.note.Note D>>

    What can we do with a elementTimespan? We can get its Part object or the
    Part object name

    ::

        >>> elementTimespan.part
        <music21.stream.Part Tenor>
        >>> elementTimespan.partName
        u'Tenor'

    Find out what measure it's in:

    ::

        >>> elementTimespan.measureNumber
        2
        >>> elementTimespan.measureStartOffset
        5.0

    The position in the measure is given by subtracting that from the
    .startOffset:

    ::

        >>> elementTimespan.startOffset - elementTimespan.measureStartOffset
        1.5


        >>> elementTimespan.beatStrength
        0.125
        >>> elementTimespan.element
        <music21.note.Note D>

    These are not dynamic, so changing the Score object does not change the
    measureNumber, beatStrength, etc.
    '''

    ### CLASS VARIABLES ###

    __slots__ = (
        '_beatStrength',
        '_element',
        '_measureStartOffset',
        '_measureStopOffset',
        '_parentage',
        '_startOffset',
        '_stopOffset',
        )

    ### INITIALIZER ###

    def __init__(
        self,
        element=None,
        beatStrength=None,
        measureStartOffset=None,
        measureStopOffset=None,
        parentage=None,
        startOffset=None,
        stopOffset=None,
        ):
        #from music21 import stream
        self._element = element
        if parentage is not None:
            parentage = tuple(parentage)
            #assert isinstance(parentage[0], stream.Measure), \
            #    parentage[0]
            #assert isinstance(parentage[-1], stream.Score), \
            #    parentage[-1]
        self._parentage = parentage
        if beatStrength is not None:
            beatStrength = float(beatStrength)
        self._beatStrength = beatStrength
        if startOffset is not None:
            startOffset = float(startOffset)
        self._startOffset = startOffset
        if stopOffset is not None:
            stopOffset = float(stopOffset)
        self._stopOffset = stopOffset
        if startOffset is not None and stopOffset is not None:
            assert startOffset <= stopOffset, (startOffset, stopOffset)
        if measureStartOffset is not None:
            measureStartOffset = float(measureStartOffset)
        self._measureStartOffset = measureStartOffset
        if measureStopOffset is not None:
            measureStopOffset = float(measureStopOffset)
        self._measureStopOffset = measureStopOffset
        if measureStartOffset is not None and measureStopOffset is not None:
            assert measureStartOffset <= measureStopOffset

    ### SPECIAL METHODS ###

    def __repr__(self):
        return '<{} {}:{} {!r}>'.format(
            type(self).__name__,
            self.startOffset,
            self.stopOffset,
            self.element,
            )

    ### PUBLIC METHODS ###

    def mergeWith(self, elementTimespan):
        assert isinstance(elementTimespan, type(self))
        assert (self.stopOffset == elementTimespan.startOffset) or \
            (elementTimespan.stopOffset == self.startOffset)
        assert self.pitches == elementTimespan.pitches
        if self.startOffset < elementTimespan.startOffset:
            mergedElementTimespan = self.new(
                stopOffset=elementTimespan.stopOffset,
                )
        else:
            mergedElementTimespan = elementTimespan.new(
                stopOffset=self.stopOffset,
                )
        return mergedElementTimespan

    def new(
        self,
        beatStrength=None,
        element=None,
        measureStartOffset=None,
        measureStopOffset=None,
        startOffset=None,
        stopOffset=None,
        ):
        if beatStrength is None:
            beatStrength = self.beatStrength
        element = element or self.element
        if measureStartOffset is None:
            measureStartOffset = self.measureStartOffset
        if measureStopOffset is None:
            measureStopOffset = self.measureStopOffset
        if startOffset is None:
            startOffset = self.startOffset
        if stopOffset is None:
            stopOffset = self.stopOffset
        return type(self)(
            beatStrength=beatStrength,
            element=element,
            measureStartOffset=measureStartOffset,
            measureStopOffset=measureStopOffset,
            parentage=self.parentage,
            startOffset=startOffset,
            stopOffset=stopOffset,
            )

    def splitAt(self, offset):
        r'''
        Split elementTimespan at `offset`.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(0)
            >>> timespan = verticality.startTimespans[0]
            >>> timespan
            <ElementTimespan 0.0:0.5 <music21.note.Note C#>>

        ::

            >>> for shard in timespan.splitAt(0.25):
            ...     shard
            ...
            <ElementTimespan 0.0:0.25 <music21.note.Note C#>>
            <ElementTimespan 0.25:0.5 <music21.note.Note C#>>

        ::

            >>> timespan.splitAt(1000)
            (<ElementTimespan 0.0:0.5 <music21.note.Note C#>>,)

        '''

        if offset < self.startOffset or self.stopOffset < offset:
            return (self,)
        left = self.new(stopOffset=offset)
        right = self.new(startOffset=offset)
        return left, right

    ### PUBLIC PROPERTIES ###

    @property
    def beatStrength(self):
        r'''
        The elementTimespan's element's beat-strength.

        This may be overriden during instantiation by passing in a custom
        beat-strength. That can be useful when you are generating new
        elementTimespans based on old ones, and want to maintain pitch
        information from the old elementTimespan but change the start offset to
        reflect that of another timespan.
        '''
        if self._beatStrength is not None:
            return self._beatStrength
        elif self._element is None:
            return None
        return self._element.beatStrength

    @property
    def quarterLength(self):
        return self.stopOffset - self.startOffset

    @property
    def element(self):
        r'''
        The elementTimespan's element.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> elementTimespan.element
            <music21.note.Note A>

        '''
        return self._element

    @property
    def measureNumber(self):
        r'''
        The measure number of the measure containing the element.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> elementTimespan.measureNumber
            1

        '''
        from music21 import stream
        for x in self.parentage:
            if not isinstance(x, stream.Measure):
                continue
            return x.measureNumber
        return None

    @property
    def measureStartOffset(self):
        return self._measureStartOffset

    @property
    def measureStopOffset(self):
        return self._measureStopOffset

    @property
    def parentage(self):
        r'''
        The Stream hierarchy above the elementTimespan's element.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> for x in elementTimespan.parentage:
            ...     x
            ...
            <music21.stream.Measure 1 offset=1.0>
            <music21.stream.Part Soprano>
            <music21.stream.Score ...>

        '''
        return self._parentage

    @property
    def part(self):
        from music21 import stream
        for x in self.parentage:
            if not isinstance(x, stream.Part):
                continue
            return x
        return None

    @property
    def partName(self):
        r'''
        The part name of the part containing the elementTimespan's element.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> elementTimespan.partName
            u'Soprano'

        '''
        part = self.part
        if part is None:
            return None
        for element in part:
            if isinstance(element, instrument.Instrument):
                return element.partName
        return None

    @property
    def pitches(self):
        r'''
        Gets the pitches of the element wrapped by this elementTimespan.

        This treats notes as chords.
        '''
        result = []
        if hasattr(self.element, 'pitches'):
            result.extend(self.element.pitches)
        result.sort()
        return tuple(result)

    @property
    def startOffset(self):
        r'''
        The start offset of the elementTimespan's element, relative to its
        containing score.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> elementTimespan.startOffset
            1.0

        '''
        return self._startOffset

    @property
    def stopOffset(self):
        r'''
        The stop offset of the elementTimespan's element, relative to its
        containing score.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> elementTimespan = verticality.startTimespans[0]
            >>> elementTimespan.stopOffset
            2.0

        '''
        return self._stopOffset


class Horizontality(collections.Sequence):
    r'''
    A horizontality of consecutive elementTimespan objects.
    '''

    ### CLASS VARIABLES ###

    __slots__ = (
        '_timespans',
        )

    ### INITIALIZER ###

    def __init__(self,
        timespans=None,
        ):
        assert isinstance(timespans, collections.Sequence)
        assert len(timespans)
        assert all(hasattr(x, 'startOffset') and hasattr(x, 'stopOffset')
            for x in timespans)
        self._timespans = tuple(timespans)

    ### SPECIAL METHODS ###

    def __getitem__(self, item):
        return self._timespans[item]

    def __len__(self):
        return len(self._timespans)

    def __repr__(self):
        pitch_strings = []
        for x in self:
            string = '({},)'.format(', '.join(
                y.nameWithOctave for y in x.pitches))
            pitch_strings.append(string)
        return '<{}: {}>'.format(
            type(self).__name__,
            ' '.join(pitch_strings),
            )

    ### PROPERTIES ###

    @property
    def hasPassingTone(self):
        r'''
        Is true if the horizontality contains a passing tone.
        '''
        if len(self) < 3:
            return False
        elif not all(len(x.pitches) for x in self):
            return False
        pitches = (
            self[0].pitches[0],
            self[1].pitches[0],
            self[2].pitches[0],
            )
        if pitches[0] < pitches[1] < pitches[2]:
            return True
        elif pitches[0] > pitches[1] > pitches[2]:
            return True
        return False

    @property
    def hasNeighborTone(self):
        r'''
        Is true if the horizontality contains a neighbor tone.
        '''
        if len(self) < 3:
            return False
        elif not all(len(x.pitches) for x in self):
            return False
        pitches = (
            self[0].pitches[0],
            self[1].pitches[0],
            self[2].pitches[0],
            )
        if pitches[0] == pitches[2]:
            if abs(pitches[1].ps - pitches[0].ps) < 3:
                return True
        return False


class Verticality(object):
    r'''
    A collection of information about elements that are sounding at a given
    offset or just finished at that offset or are continuing from before, etc..


    Create a timespan-stream from a score:

    ::

        >>> score = corpus.parse('bwv66.6')
        >>> tree = stream.timespans.TimespanCollection(score)


    Find the verticality at offset 6.5, or beat 2.5 of measure 2 (there's a one
    beat pickup)

    ::

        >>> verticality = tree.getVerticalityAt(6.5)
        >>> verticality
        <Verticality 6.5 {E3 D4 G#4 B4}>

    The representation of a verticality gives the pitches from lowest to
    highest (in sounding notes).


    A verticality knows its startOffset, but because elements might end at
    different times, it doesn't know its stopOffset

    ::

        >>> verticality.startOffset
        6.5
        >>> verticality.stopOffset
        Traceback (most recent call last):
        AttributeError: 'Verticality' object has no attribute 'stopOffset'

    However, we can find when the next verticality starts by looking at the
    nextVerticality

    ::

        >>> verticality.nextVerticality
        <Verticality 7.0 {A2 C#4 E4 A4}>
        >>> verticality.nextVerticality.startOffset
        7.0

    Or more simply:

    ::

        >>> verticality.nextStartOffset
        7.0

    (There is also a previousVerticality, but not a previousStartOffset)

    What we just demonstrated is actually very powerful: a Verticality keeps a
    record of exactly where it is in the timespanStream -- scores can be
    recreated with this information.

    Getting back to the task at hand, we can find all the elementTimespans (and
    from there the elements) that start at exactly 6.5.  There's one, it's a
    passing tone D in the tenor and it lastes from offset 6.5 to offset 7.0,
    with respect to the beginning of the score, not to the beginning of the
    measure.  That is to say, it's an eighth note

    ::

        >>> verticality.startTimespans
        (<ElementTimespan 6.5:7.0 <music21.note.Note D>>,)


    And we can get all the elementTimespans that were already sounding at the
    moment (that is to say, the non-passing tones):

    ::

        >>> verticality.overlapTimespans
        (<ElementTimespan 6.0:7.0 <music21.note.Note B>>,
         <ElementTimespan 6.0:7.0 <music21.note.Note G#>>,
         <ElementTimespan 6.0:7.0 <music21.note.Note E>>)

    And we can get all the things that stop right at this moment.  It's the E
    in the tenor preceding the passing tone D:

    ::

        >>> verticality.stopTimespans
        (<ElementTimespan 6.0:6.5 <music21.note.Note E>>,)

    '''

    ### CLASS VARIABLES ###

    __slots__ = (
        '_timespanStream',
        '_overlapTimespans',
        '_startTimespans',
        '_startOffset',
        '_stopTimespans',
        )

    ### INITIALIZER ###

    def __init__(
        self,
        timespanStream=None,
        overlapTimespans=None,
        startTimespans=None,
        startOffset=None,
        stopTimespans=None,
        ):
        assert isinstance(timespanStream, (TimespanCollection, type(None)))
        self._timespanStream = timespanStream
        self._startOffset = startOffset
        assert isinstance(startTimespans, tuple)
        assert isinstance(stopTimespans, (tuple, type(None)))
        assert isinstance(overlapTimespans, (tuple, type(None)))
        self._startTimespans = startTimespans
        self._stopTimespans = stopTimespans
        self._overlapTimespans = overlapTimespans

    ### SPECIAL METHODS ###

    def __repr__(self):
        sortedPitches = sorted(self.pitchSet)
        return '<{} {} {{{}}}>'.format(
            type(self).__name__,
            self.startOffset,
            ' '.join(x.nameWithOctave for x in sortedPitches)
            )

    ### PUBLIC PROPERTIES ###

    @property
    def bassTimespan(self):
        r'''
        Gets the bass timespan in this verticality.

        This is CURRENTLY the lowest PART not the lowest note necessarily.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> verticality
            <Verticality 1.0 {F#3 C#4 F#4 A4}>

        ::

            >>> verticality.bassTimespan
            <ElementTimespan 1.0:2.0 <music21.note.Note F#>>

        '''
        pitches = sorted(self.pitchSet)
        lowestPitch = pitches[0]
        timespans = self.startTimespans + self.overlapTimespans
        bassTimespans = []
        for timespan in timespans:
            pitches = timespan.pitches
            if lowestPitch in pitches:
                bassTimespans.append(timespan)
        if bassTimespans:
            bassTimespans.sort(
                key=lambda x: x.part.getInstrument().partId,
                reverse=True,
                )
            return bassTimespans[0]
        return None

    @property
    def beatStrength(self):
        r'''
        Gets the beat strength of a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> verticality.beatStrength
            1.0

        '''
        thisElementTimespan = self.startTimespans[0]
        if self.startOffset == 1.0:
            pass  # debugging; delete
        return thisElementTimespan.beatStrength

    @property
    def degreeOfOverlap(self):
        '''
        Counts the number of things sounding at this moment
        '''

        return len(self.startTimespans) + len(self.overlapTimespans)

    def toChord(self):
        '''
        creates a chord object from the verticality
        '''
        pitchSet = sorted(self.pitchSet)
        testChord = chord.Chord(pitchSet)
        return testChord

    @property
    def isConsonant(self):
        r'''
        Is true when the pitch set of a verticality is consonant.

        ::

                >>> score = corpus.parse('bwv66.6')
                >>> tree = stream.timespans.TimespanCollection(score)
                >>> verticalities = list(tree.iterateVerticalities())
                >>> for verticality in verticalities[:10]:
                ...     print verticality, verticality.isConsonant
                ...
                <Verticality 0.0 {A3 E4 C#5}> True
                <Verticality 0.5 {G#3 B3 E4 B4}> True
                <Verticality 1.0 {F#3 C#4 F#4 A4}> True
                <Verticality 2.0 {G#3 B3 E4 B4}> True
                <Verticality 3.0 {A3 E4 C#5}> True
                <Verticality 4.0 {G#3 B3 E4 E5}> True
                <Verticality 5.0 {A3 E4 C#5}> True
                <Verticality 5.5 {C#3 E4 A4 C#5}> True
                <Verticality 6.0 {E3 E4 G#4 B4}> True
                <Verticality 6.5 {E3 D4 G#4 B4}> False

        '''
        return self.toChord().isConsonant()

    @property
    def measureNumber(self):
        r'''
        Gets the measure number of the verticality's starting elements.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(7.0)
            >>> verticality.measureNumber
            2

        '''
        return self.startTimespans[0].measureNumber

    @property
    def nextStartOffset(self):
        r'''
        Gets the next start-offset in the verticality's offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> verticality.nextStartOffset
            2.0

        '''
        tree = self._timespanStream
        if tree is None:
            return None
        startOffset = tree.getStartOffsetAfter(self.startOffset)
        return startOffset

    @property
    def nextVerticality(self):
        r'''
        Gets the next verticality after a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> print verticality
            <Verticality 1.0 {F#3 C#4 F#4 A4}>

        ::

            >>> nextVerticality = verticality.nextVerticality
            >>> print nextVerticality
            <Verticality 2.0 {G#3 B3 E4 B4}>

        Verticality objects created by an offset-tree hold a reference back to
        that offset-tree. This means that they determine their next or previous
        verticality dynamically based on the state of the offset-tree only when
        asked. Because of this, it is safe to mutate the offset-tree by
        inserting or removing timespans while iterating over it.

        ::

            >>> tree.remove(nextVerticality.startTimespans)
            >>> verticality.nextVerticality
            <Verticality 3.0 {A3 E4 C#5}>

        '''
        tree = self._timespanStream
        if tree is None:
            return None
        startOffset = tree.getStartOffsetAfter(self.startOffset)
        if startOffset is None:
            return None
        return tree.getVerticalityAt(startOffset)

    @property
    def overlapTimespans(self):
        r'''
        Gets timespans overlapping the start offset of a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(0.5)
            >>> verticality.overlapTimespans
            (<ElementTimespan 0.0:1.0 <music21.note.Note E>>,)

        '''
        return self._overlapTimespans

    @property
    def pitchSet(self):
        r'''
        Gets the pitch set of all elements in a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> for pitch in sorted(verticality.pitchSet):
            ...     pitch
            ...
            <music21.pitch.Pitch F#3>
            <music21.pitch.Pitch C#4>
            <music21.pitch.Pitch F#4>
            <music21.pitch.Pitch A4>

        '''
        pitchSet = set()
        for elementTimespan in self.startTimespans:
            element = elementTimespan.element
            pitches = [x.nameWithOctave for x in element.pitches]
            pitchSet.update(pitches)
        for elementTimespan in self.overlapTimespans:
            element = elementTimespan.element
            pitches = [x.nameWithOctave for x in element.pitches]
#             for p in pitches:
#                 if p.tie is None:
#                     p.tie = tie.Tie('stop')
            pitchSet.update(pitches)
        pitchSet = set([pitch.Pitch(x) for x in pitchSet])
        return pitchSet

    @property
    def pitchClassSet(self):
        r'''
        Gets the pitch-class set of all elements in a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> for pitchClass in sorted(verticality.pitchClassSet):
            ...     pitchClass
            ...
            <music21.pitch.Pitch C#>
            <music21.pitch.Pitch F#>
            <music21.pitch.Pitch A>

        '''
        pitchClassSet = set()
        for currentPitch in self.pitchSet:
            pitchClass = pitch.Pitch(currentPitch.name)
            pitchClassSet.add(pitchClass)
        return pitchClassSet

    @property
    def previousVerticality(self):
        r'''
        Gets the previous verticality before a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> print verticality
            <Verticality 1.0 {F#3 C#4 F#4 A4}>

        ::

            >>> previousVerticality = verticality.previousVerticality
            >>> print previousVerticality
            <Verticality 0.5 {G#3 B3 E4 B4}>

        Verticality objects created by an offset-tree hold a reference back to
        that offset-tree. This means that they determine their next or previous
        verticality dynamically based on the state of the offset-tree only when
        asked. Because of this, it is safe to mutate the offset-tree by
        inserting or removing timespans while iterating over it.

        ::

            >>> tree.remove(previousVerticality.startTimespans)
            >>> verticality.previousVerticality
            <Verticality 0.0 {A3 E4 C#5}>

        '''
        tree = self._timespanStream
        if tree is None:
            return None
        startOffset = tree.getStartOffsetBefore(self.startOffset)
        if startOffset is None:
            return None
        return tree.getVerticalityAt(startOffset)

    @property
    def startOffset(self):
        r'''
        Gets the start offset of a verticality.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> verticality.startOffset
            1.0

        '''
        return self._startOffset

    @property
    def startTimespans(self):
        r'''
        Gets the timespans starting at a verticality's start offset.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> for timespan in verticality.startTimespans:
            ...     timespan
            ...
            <ElementTimespan 1.0:2.0 <music21.note.Note A>>
            <ElementTimespan 1.0:2.0 <music21.note.Note F#>>
            <ElementTimespan 1.0:2.0 <music21.note.Note C#>>
            <ElementTimespan 1.0:2.0 <music21.note.Note F#>>

        '''
        return self._startTimespans

    @property
    def stopTimespans(self):
        r'''
        Gets the timespans stopping at a verticality's start offset.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> verticality = tree.getVerticalityAt(1.0)
            >>> for timespan in verticality.stopTimespans:
            ...     timespan
            ...
            <ElementTimespan 0.0:1.0 <music21.note.Note E>>
            <ElementTimespan 0.5:1.0 <music21.note.Note B>>
            <ElementTimespan 0.5:1.0 <music21.note.Note B>>
            <ElementTimespan 0.5:1.0 <music21.note.Note G#>>

        '''
        return self._stopTimespans


class VerticalitySequence(collections.Sequence):
    r'''
    A segment of verticalities.
    '''

    ### INITIALIZER ###

    def __init__(self, verticalities):
        self._verticalities = tuple(verticalities)

    ### SPECIAL METHODS ###

    def __getitem__(self, item):
        return self._verticalities[item]

    def __len__(self):
        return len(self._verticalities)

    def __repr__(self):
        string = '<VerticalitySequence: [\n\t{}\n\t]>'.format(
            ',\n\t'.join(repr(x) for x in self))
        return string

    ### PUBLIC METHODS ###

    def hasNeighborTone(self, partIdentifier, unaccentedOnly=False):
        assert len(self) == 3
        pass

    def hasPassingTone(self, partIdentifier, unaccentedOnly=False):
        assert len(self) == 3
        pass


class TimespanCollection(object):
    r'''
    A datastructure for efficiently slicing a score.

    This datastructure stores timespans: objects which implement both a
    `startOffset` and `stopOffset` property. It provides fast lookups of such
    objects and can quickly locate vertical overlaps.

    While you can construct an offset-tree by hand, inserting timespans one at
    a time, the common use-case is to construct the offset-tree from an entire
    score at once:

    ::

        >>> bach = corpus.parse('bwv66.6')
        >>> tree = stream.timespans.TimespanCollection(bach)
        >>> print tree.getVerticalityAt(17.0)
        <Verticality 17.0 {F#3 C#4 A4}>

    All offsets are assumed to be relative to the score's origin.


    Example: How many moments in Bach are consonant and how many are dissonant:

    ::

        >>> totalCons = 0
        >>> totalDiss = 0
        >>> for v in tree.iterateVerticalities():
        ...     if v.toChord().isConsonant():
        ...        totalCons += 1
        ...     else:
        ...        totalDiss += 1
        >>> (totalCons, totalDiss)
        (34, 17)


    So 1/3 of the vertical moments in Bach are dissonant!  But is this an
    accurate perception? Let's sum up the total consonant duration vs.
    dissonant duration.

    Do it again pairwise to figure out the length (actually this won't include
    the last element)

    ::

        >>> durCons = 0
        >>> durDiss = 0
        >>> for v1, v2 in tree.iterateVerticalitiesNwise(n=2):
        ...     vDurationQL = v2.startOffset - v1.startOffset
        ...     if v1.toChord().isConsonant():
        ...        durCons += vDurationQL
        ...     else:
        ...        durDiss += vDurationQL
        >>> (durCons, durDiss)
        (25.5, 9.5)

    Remove neighbor tones from the Bach chorale:

    Here in Alto, measure 7, there's a neighbor tone E#.

    ::

        >>> bach.parts['Alto'].measure(7).show('text')
        {0.0} <music21.note.Note F#>
        {0.5} <music21.note.Note E#>
        {1.0} <music21.note.Note F#>
        {1.5} <music21.note.Note F#>
        {2.0} <music21.note.Note C#>

    We'll get rid of it and a lot of other neighbor tones.

    ::

        >>> for verticalities in tree.iterateVerticalitiesNwise(n=3):
        ...    horizontalities = tree.unwrapVerticalities(verticalities)
        ...    for unused_part, horizontality in horizontalities.items():
        ...        if horizontality.hasNeighborTone:
        ...            merged = horizontality[0].new(
        ...               stopOffset=horizontality[2].stopOffset,
        ...            ) # merged is a new ElementTimeSpan
        ...            tree.remove(horizontality[0])
        ...            tree.remove(horizontality[1])
        ...            tree.remove(horizontality[2])
        ...            tree.insert(merged)
        >>> newBach = tree.toPartwiseScore()
        >>> newBach.parts[1].measure(7).show('text')
        {0.0} <music21.note.Note F#>
        {1.5} <music21.note.Note F#>
        {2.0} <music21.note.Note C#>

    The second F# is an octave lower, so it wouldn't get merged even if
    adjacent notes were fused together (which they're not).

    ..  note::

        TimespanCollection is an implementation of an extended AVL tree. AVL
        trees are a type of binary tree, like Red-Black trees. AVL trees are
        very efficient at insertion when the objects being inserted are already
        sorted - which is usually the case with data extracted from a score.
        TimespanCollection is an extended AVL tree because each node in the
        tree keeps track of not just the start offsets of ElementTimespans
        stored at that node, but also the earliest and latest stop offset of
        all ElementTimespans stores at both that node and all nodes which are
        children of that node. This lets us quickly located ElementTimespans
        which overlap offsets or which are contained within ranges.

    TODO: newBach.parts['Alto'].measure(7).show('text') should work.
    KeyError: 'provided key (Alto) does not match any id or group'

    TODO: Doc examples for all functions, including privates.
    '''

    ### CLASS VARIABLES ###

    __slots__ = (
        '_rootNode',
        '_sourceScore',
        )

    class TimespanCollectionNode(object):
        r'''
        A node in an TimespanCollection.

        This class is only used by TimespanCollection, and should not be
        instantiated by hand. It stores a list of ElementTimespans, as well as
        various data which describes the internal structure of the tree.

            >>> startOffset = 1.0
            >>> node = stream.timespans.TimespanCollection.TimespanCollectionNode(startOffset)

        Please consult the wikipedia page for AVL tree
        (https://en.wikipedia.org/wiki/AVL_tree) for a very detailed
        description of how this works.
        '''

        ### CLASS VARIABLES ###

        __slots__ = (
            '_balance',
            '_height',
            '_leftChild',
            '_payload',
            '_rightChild',
            '_startOffset',
            '_nodeStartIndex',
            '_nodeStopIndex',
            '_stopOffsetHigh',
            '_stopOffsetLow',
            '_subtreeStartIndex',
            '_subtreeStopIndex',
            )

        ### INITIALIZER ###

        def __init__(self, startOffset):
            self._balance = 0
            self._height = 0
            self._leftChild = None
            self._nodeStartIndex = -1
            self._nodeStopIndex = -1
            self._payload = []
            self._rightChild = None
            self._startOffset = startOffset
            self._stopOffsetHigh = None
            self._stopOffsetLow = None
            self._subtreeStartIndex = -1
            self._subtreeStopIndex = -1

        ### SPECIAL METHODS ###

        def __repr__(self):
            return '<N: {} [{}:{}:{}:{}] {{{}}}>'.format(
                self.startOffset,
                self.subtreeStartIndex,
                self.nodeStartIndex,
                self.nodeStopIndex,
                self.subtreeStopIndex,
                len(self.payload),
                )

        ### PRIVATE METHODS ###

        def _debug(self):
            return '\n'.join(self._getDebugPieces())

        def _getDebugPieces(self):
            result = []
            result.append(repr(self))
            if self.leftChild:
                subresult = self.leftChild._getDebugPieces()
                result.append('\tL: {}'.format(subresult[0]))
                result.extend('\t' + x for x in subresult[1:])
            if self.rightChild:
                subresult = self.rightChild._getDebugPieces()
                result.append('\tR: {}'.format(subresult[0]))
                result.extend('\t' + x for x in subresult[1:])
            return result

        def _update(self):
            leftHeight = -1
            rightHeight = -1
            if self.leftChild is not None:
                leftHeight = self.leftChild.height
            if self.rightChild is not None:
                rightHeight = self.rightChild.height
            self._height = max(leftHeight, rightHeight) + 1
            self._balance = rightHeight - leftHeight
            return self.height

        ### PUBLIC PROPERTIES ###

        @property
        def balance(self):
            return self._balance

        @property
        def height(self):
            return self._height

        @property
        def leftChild(self):
            return self._leftChild

        @leftChild.setter
        def leftChild(self, node):
            self._leftChild = node
            self._update()

        @property
        def nodeStartIndex(self):
            return self._nodeStartIndex

        @property
        def nodeStopIndex(self):
            return self._nodeStopIndex

        @property
        def payload(self):
            r'''
            A list of ElementTimespans starting at this node's start offset,
            ordered by their stop offsets.
            '''
            return self._payload

        @property
        def rightChild(self):
            return self._rightChild

        @rightChild.setter
        def rightChild(self, node):
            self._rightChild = node
            self._update()

        @property
        def startOffset(self):
            return self._startOffset

        @property
        def stopOffsetHigh(self):
            return self._stopOffsetHigh

        @property
        def stopOffsetLow(self):
            return self._stopOffsetLow

        @property
        def subtreeStartIndex(self):
            return self._subtreeStartIndex

        @property
        def subtreeStopIndex(self):
            return self._subtreeStopIndex

    ### INITIALIZER ###

    def __init__(
        self,
        sourceScore=None,
        ):
        from music21 import stream
        self._rootNode = None
        if sourceScore is not None:
            if not isinstance(sourceScore, stream.Score):
                message = 'Score {!r}, must be an stream.Score object'.format(
                    sourceScore)
                raise TimespanCollectionException(message)
            timespans = recurseStream(sourceScore)
            self.insert(timespans)
        self._sourceScore = sourceScore

    ### SPECIAL METHODS ###

    def __contains__(self, timespan):
        r'''
        Is true when timespan collection contains `timespan`.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)

        ::

            >>> timespans[0] in tree
            True

        ::

            >>> stream.timespans.Timespan(-200, 1000) in tree
            False

        '''
        if not hasattr(timespan, 'startOffset') or \
            not hasattr(timespan, 'stopOffset'):
            message = 'Must have startOffset and stopOffset.'
            raise TimespanCollectionException(message)
        candidates = self.findTimespansStartingAt(timespan.startOffset)
        return timespan in candidates

    def __getitem__(self, i):
        r'''
        Gets timespans by integer index or slice.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)

        ::

            >>> tree[0]
            <Timespan 0 2>

        ::

            >>> tree[-1]
            <Timespan 7 7>

        ::

            >>> tree[2:5]
            [<Timespan 1 1>, <Timespan 2 3>, <Timespan 3 4>]

        ::

            >>> tree[-6:-3]
            [<Timespan 3 4>, <Timespan 4 9>, <Timespan 5 6>]

        ::

            >>> tree[-100:-200]
            []

        ::

            >>> for x in tree[:]:
            ...     x
            ...
            <Timespan 0 2>
            <Timespan 0 9>
            <Timespan 1 1>
            <Timespan 2 3>
            <Timespan 3 4>
            <Timespan 4 9>
            <Timespan 5 6>
            <Timespan 5 8>
            <Timespan 6 8>
            <Timespan 7 7>

        '''
        def recurseByIndex(node, index):
            if node.nodeStartIndex <= index < node.nodeStopIndex:
                return node.payload[index - node.nodeStartIndex]
            elif node.leftChild and index < node.nodeStartIndex:
                return recurseByIndex(node.leftChild, index)
            elif node.rightChild and node.nodeStopIndex <= index:
                return recurseByIndex(node.rightChild, index)

        def recurseBySlice(node, start, stop):
            result = []
            if node is None:
                return result
            if start < node.nodeStartIndex and node.leftChild:
                result.extend(recurseBySlice(node.leftChild, start, stop))
            if start < node.nodeStopIndex and node.nodeStartIndex < stop:
                nodeStart = start - node.nodeStartIndex
                if nodeStart < 0:
                    nodeStart = 0
                nodeStop = stop - node.nodeStartIndex
                result.extend(node.payload[nodeStart:nodeStop])
            if node.nodeStopIndex <= stop and node.rightChild:
                result.extend(recurseBySlice(node.rightChild, start, stop))
            return result
        if isinstance(i, int):
            if self._rootNode is None:
                raise IndexError
            if i < 0:
                i = self._rootNode.subtreeStopIndex + i
            if i < 0 or self._rootNode.subtreeStopIndex <= i:
                raise IndexError
            return recurseByIndex(self._rootNode, i)
        elif isinstance(i, slice):
            if self._rootNode is None:
                return []
            indices = i.indices(self._rootNode.subtreeStopIndex)
            start, stop = indices[0], indices[1]
            return recurseBySlice(self._rootNode, start, stop)
        raise TypeError('Indices must be integers or slices, got {}'.format(i))

    def __iter__(self):
        r'''
        Iterates through all the elementTimespans in the offset tree.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)

        ::

            >>> for x in tree:
            ...     x
            ...
            <Timespan 0 2>
            <Timespan 0 9>
            <Timespan 1 1>
            <Timespan 2 3>
            <Timespan 3 4>
            <Timespan 4 9>
            <Timespan 5 6>
            <Timespan 5 8>
            <Timespan 6 8>
            <Timespan 7 7>

        '''
        def recurse(node):
            if node is not None:
                if node.leftChild is not None:
                    for timespan in recurse(node.leftChild):
                        yield timespan
                for timespan in node.payload:
                    yield timespan
                if node.rightChild is not None:
                    for timespan in recurse(node.rightChild):
                        yield timespan
        return recurse(self._rootNode)

    def __len__(self):
        r'''Gets the length of the timespan collection.

        ::

            >>> tree = stream.timespans.TimespanCollection()
            >>> len(tree)
            0

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree.insert(timespans)
            >>> len(tree)
            10

        ::

            >>> tree.remove(timespans)
            >>> len(tree)
            0

        '''
        if self._rootNode is None:
            return 0
        return self._rootNode.subtreeStopIndex

    def __setitem__(self, i, new):
        r'''
        Sets timespans at index `i` to `new`.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)
            >>> tree[0] = stream.timespans.Timespan(-1, 6)
            >>> for x in tree:
            ...     x
            ...
            <Timespan -1 6>
            <Timespan 0 9>
            <Timespan 1 1>

        ::

            >>> tree[1:] = [stream.timespans.Timespan(10, 20)]
            >>> for x in tree:
            ...     x
            ...
            <Timespan -1 6>
            <Timespan 10 20>

        '''
        if isinstance(i, (int, slice)):
            old = self[i]
            self.remove(old)
            self.insert(new)
        else:
            message = 'Indices must be ints or slices, got {}'.format(i)
            raise TypeError(message)

    def __str__(self):
        r'''
        Gets string representation of the timespan collection.

        Useful only for debugging its internal node structure.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)

        ::

            >>> print str(tree)
            <N: 3 [0:4:5:10] {1}>
                L: <N: 1 [0:2:3:4] {1}>
                    L: <N: 0 [0:0:2:2] {2}>
                    R: <N: 2 [3:3:4:4] {1}>
                R: <N: 5 [5:6:8:10] {2}>
                    L: <N: 4 [5:5:6:6] {1}>
                    R: <N: 6 [8:8:9:10] {1}>
                        R: <N: 7 [9:9:10:10] {1}>

        '''
        if self._rootNode is not None:
            return self._rootNode._debug()
        return ''

    ### PRIVATE METHODS ###

    def _insert(self, node, startOffset):
        r'''
        Inserts a node at `startOffset` in the subtree rooted on `node`.

        Used internally by TimespanCollection.

        Returns a node.
        '''
        if node is None:
            return TimespanCollection.TimespanCollectionNode(startOffset)
        if startOffset < node.startOffset:
            node.leftChild = self._insert(node.leftChild, startOffset)
        elif node.startOffset < startOffset:
            node.rightChild = self._insert(node.rightChild, startOffset)
        return self._rebalance(node)

    def _rebalance(self, node):
        r'''
        Rebalances the subtree rooted at `node`.

        Used internally by TimespanCollection.

        Returns a node.
        '''
        if node is not None:
            if 1 < node.balance:
                if 0 <= node.rightChild.balance:
                    node = self._rotateRightRight(node)
                else:
                    node = self._rotateRightLeft(node)
            elif node.balance < -1:
                if node.leftChild.balance <= 0:
                    node = self._rotateLeftLeft(node)
                else:
                    node = self._rotateLeftRight(node)
            assert -1 <= node.balance <= 1
        return node

    def _remove(self, node, startOffset):
        r'''
        Removes a node at `startOffset` in the subtree rooted on `node`.

        Used internally by TimespanCollection.

        Returns a node.
        '''
        if node is not None:
            if node.startOffset == startOffset:
                if node.leftChild and node.rightChild:
                    nextNode = node.rightChild
                    while nextNode.leftChild:
                        nextNode = nextNode.leftChild
                    node._startOffset = nextNode._startOffset
                    node._payload = nextNode._payload
                    node.rightChild = self._remove(
                        node.rightChild, nextNode.startOffset)
                else:
                    node = node.leftChild or node.rightChild
            elif startOffset < node.startOffset:
                node.leftChild = self._remove(node.leftChild, startOffset)
            elif node.startOffset < startOffset:
                node.rightChild = self._remove(node.rightChild, startOffset)
        return self._rebalance(node)

    def _rotateLeftLeft(self, node):
        r'''
        Rotates a node left twice.

        Used internally by TimespanCollection during tree rebalancing.

        Returns a node.
        '''
        nextNode = node.leftChild
        node.leftChild = nextNode.rightChild
        nextNode.rightChild = node
        return nextNode

    def _rotateLeftRight(self, node):
        r'''
        Rotates a node right twice.

        Used internally by TimespanCollection during tree rebalancing.

        Returns a node.
        '''
        node.leftChild = self._rotateRightRight(node.leftChild)
        nextNode = self._rotateLeftLeft(node)
        return nextNode

    def _rotateRightLeft(self, node):
        r'''
        Rotates a node right, then left.

        Used internally by TimespanCollection during tree rebalancing.

        Returns a node.
        '''
        node.rightChild = self._rotateLeftLeft(node.rightChild)
        nextNode = self._rotateRightRight(node)
        return nextNode

    def _rotateRightRight(self, node):
        r'''
        Rotates a node left, then right.

        Used internally by TimespanCollection during tree rebalancing.

        Returns a node.
        '''
        nextNode = node.rightChild
        node.rightChild = nextNode.leftChild
        nextNode.leftChild = node
        return nextNode

    def _search(self, node, startOffset):
        r'''
        Searches for a node whose startOffset is `startOffset` in the subtree
        rooted on `node`.

        Used internally by TimespanCollection.

        Returns a node.
        '''
        if node is not None:
            if node.startOffset == startOffset:
                return node
            elif node.leftChild and startOffset < node.startOffset:
                return self._search(node.leftChild, startOffset)
            elif node.rightChild and node.startOffset < startOffset:
                return self._search(node.rightChild, startOffset)
        return None

    def _updateIndices(
        self,
        node,
        ):
        r'''
        Traverses the tree structure and updates cached indices which keep
        track of the index of the timespans stored at each node, and of the
        maximum and minimum indices of the subtrees rooted at each node.

        Used internally by TimespanCollection.

        Returns none.
        '''
        def recurse(
            node,
            parentStopIndex=None,
            ):
            if node is None:
                return
            if node.leftChild is not None:
                recurse(
                    node.leftChild,
                    parentStopIndex=parentStopIndex,
                    )
                node._nodeStartIndex = node.leftChild.subtreeStopIndex
                node._subtreeStartIndex = node.leftChild.subtreeStartIndex
            elif parentStopIndex is None:
                node._nodeStartIndex = 0
                node._subtreeStartIndex = 0
            else:
                node._nodeStartIndex = parentStopIndex
                node._subtreeStartIndex = parentStopIndex
            node._nodeStopIndex = node.nodeStartIndex + len(node.payload)
            node._subtreeStopIndex = node.nodeStopIndex
            if node.rightChild is not None:
                recurse(
                    node.rightChild,
                    parentStopIndex=node.nodeStopIndex,
                    )
                node._subtreeStopIndex = node.rightChild.subtreeStopIndex
        recurse(node)

    def _updateOffsets(
        self,
        node,
        ):
        r'''
        Traverses the tree structure and updates cached maximum and minimum
        stop offset values for the subtrees rooted at each node.

        Used internaly by TimespanCollection.

        Returns a node.
        '''
        if node is None:
            return
        stopOffsetLow = min(x.stopOffset for x in node.payload)
        stopOffsetHigh = max(x.stopOffset for x in node.payload)
        if node.leftChild:
            leftChild = self._updateOffsets(
                node.leftChild,
                )
            if leftChild.stopOffsetLow < stopOffsetLow:
                stopOffsetLow = leftChild.stopOffsetLow
            if stopOffsetHigh < leftChild.stopOffsetHigh:
                stopOffsetHigh = leftChild.stopOffsetHigh
        if node.rightChild:
            rightChild = self._updateOffsets(
                node.rightChild,
                )
            if rightChild.stopOffsetLow < stopOffsetLow:
                stopOffsetLow = rightChild.stopOffsetLow
            if stopOffsetHigh < rightChild.stopOffsetHigh:
                stopOffsetHigh = rightChild.stopOffsetHigh
        node._stopOffsetLow = stopOffsetLow
        node._stopOffsetHigh = stopOffsetHigh
        return node

    ### PUBLIC METHODS ###

    def copy(self):
        r'''
        Creates a new offset-tree with the same timespans as this offset-tree.

        This is analogous to `dict.copy()`.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> newTree = tree.copy()

        '''
        newTree = type(self)()
        newTree._sourceScore = self.sourceScore
        newTree.insert([x for x in self])
        return newTree

    def findNextElementTimespanInSamePart(self, elementTimespan):
        '''

        '''
        if not isinstance(elementTimespan, ElementTimespan):
            message = 'ElementTimespan {!r}, must be an ElementTimespan'.format(
                elementTimespan)
            raise TimespanCollectionException(message)
        verticality = self.getVerticalityAt(elementTimespan.startOffset)
        while verticality is not None:
            verticality = verticality.nextVerticality
            if verticality is None:
                return None
            for nextElementTimespan in verticality.startTimespans:
                if nextElementTimespan.part is elementTimespan.part:
                    return nextElementTimespan

    def findPreviousElementTimespanInSamePart(self, elementTimespan):
        if not isinstance(elementTimespan, ElementTimespan):
            message = 'ElementTimespan {!r}, must be an ElementTimespan'.format(
                elementTimespan)
            raise TimespanCollectionException(message)
        verticality = self.getVerticalityAt(elementTimespan.startOffset)
        while verticality is not None:
            verticality = verticality.previousVerticality
            if verticality is None:
                return None
            for previousElementTimespan in verticality.startTimespans:
                if previousElementTimespan.part is elementTimespan.part:
                    return previousElementTimespan

    def findTimespansStartingAt(self, offset):
        r'''
        Finds timespans in this offset-tree which start at `offset`.

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for timespan in tree.findTimespansStartingAt(0.5):
            ...     timespan
            ...
            <ElementTimespan 0.5:1.0 <music21.note.Note B>>
            <ElementTimespan 0.5:1.0 <music21.note.Note B>>
            <ElementTimespan 0.5:1.0 <music21.note.Note G#>>

        '''
        results = []
        node = self._search(self._rootNode, offset)
        if node is not None:
            results.extend(node.payload)
        return tuple(results)

    def findTimespansStoppingAt(self, offset):
        r'''
        Finds timespans in this offset-tree which stop at `offset`.

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for timespan in tree.findTimespansStoppingAt(0.5):
            ...     timespan
            ...
            <ElementTimespan 0.0:0.5 <music21.note.Note C#>>
            <ElementTimespan 0.0:0.5 <music21.note.Note A>>
            <ElementTimespan 0.0:0.5 <music21.note.Note A>>

        '''
        def recurse(node, offset):
            result = []
            if node.stopOffsetLow <= offset <= node.stopOffsetHigh:
                for timespan in node.payload:
                    if timespan.stopOffset == offset:
                        result.append(timespan)
                if node.leftChild is not None:
                    result.extend(recurse(node.leftChild, offset))
                if node.rightChild is not None:
                    result.extend(recurse(node.rightChild, offset))
            return result
        results = recurse(self._rootNode, offset)
        results.sort(key=lambda x: (x.startOffset, x.stopOffset))
        return tuple(results)

    def findTimespansOverlapping(self, offset):
        r'''
        Finds timespans in this offset-tree which overlap `offset`.

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for timespan in tree.findTimespansOverlapping(0.5):
            ...     timespan
            ...
            <ElementTimespan 0.0:1.0 <music21.note.Note E>>

        '''
        def recurse(node, offset, indent=0):
            result = []
            if node is not None:
                if node.startOffset < offset < node.stopOffsetHigh:
                    result.extend(recurse(node.leftChild, offset, indent + 1))
                    for timespan in node.payload:
                        if offset < timespan.stopOffset:
                            result.append(timespan)
                    result.extend(recurse(node.rightChild, offset, indent + 1))
                elif offset <= node.startOffset:
                    result.extend(recurse(node.leftChild, offset, indent + 1))
            return result
        results = recurse(self._rootNode, offset)
        results.sort(key=lambda x: (x.startOffset, x.stopOffset))
        return tuple(results)

    def getStartOffsetAfter(self, offset):
        r'''
        Gets start offset after `offset`.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.getStartOffsetAfter(0.5)
            1.0

        ::

            >>> tree.getStartOffsetAfter(35) is None
            True

        Returns none if no succeeding offset exists.
        '''
        def recurse(node, offset):
            if node is None:
                return None
            result = None
            if node.startOffset <= offset and node.rightChild:
                result = recurse(node.rightChild, offset)
            elif offset < node.startOffset:
                result = recurse(node.leftChild, offset) or node
            return result
        result = recurse(self._rootNode, offset)
        if result is None:
            return None
        return result.startOffset

    def getStartOffsetBefore(self, offset):
        r'''
        Gets the start offset immediately preceding `offset` in this
        offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.getStartOffsetBefore(100)
            35.0

        ::

            >>> tree.getStartOffsetBefore(0) is None
            True

        Return none if no preceding offset exists.
        '''
        def recurse(node, offset):
            if node is None:
                return None
            result = None
            if node.startOffset < offset:
                result = recurse(node.rightChild, offset) or node
            elif offset <= node.startOffset and node.leftChild:
                result = recurse(node.leftChild, offset)
            return result
        result = recurse(self._rootNode, offset)
        if result is None:
            return None
        return result.startOffset

    def getVerticalityAt(self, offset):
        r'''
        Gets the verticality in this offset-tree which starts at `offset`.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.getVerticalityAt(2.5)
            <Verticality 2.5 {G#3 B3 E4 B4}>

        Return verticality.
        '''
        startTimespans = self.findTimespansStartingAt(offset)
        stopTimespans = self.findTimespansStoppingAt(offset)
        overlapTimespans = self.findTimespansOverlapping(offset)
        verticality = Verticality(
            timespanStream=self,
            overlapTimespans=overlapTimespans,
            startTimespans=startTimespans,
            startOffset=offset,
            stopTimespans=stopTimespans,
            )
        return verticality

    def index(self, timespan):
        r'''
        Gets index of `timespan` in tree.

        ::

            >>> timespans = [
            ...     stream.timespans.Timespan(0, 2),
            ...     stream.timespans.Timespan(0, 9),
            ...     stream.timespans.Timespan(1, 1),
            ...     stream.timespans.Timespan(2, 3),
            ...     stream.timespans.Timespan(3, 4),
            ...     stream.timespans.Timespan(4, 9),
            ...     stream.timespans.Timespan(5, 6),
            ...     stream.timespans.Timespan(5, 8),
            ...     stream.timespans.Timespan(6, 8),
            ...     stream.timespans.Timespan(7, 7),
            ...     ]
            >>> tree = stream.timespans.TimespanCollection()
            >>> tree.insert(timespans)

        ::

            >>> for timespan in timespans:
            ...     print timespan, tree.index(timespan)
            ...
            <Timespan 0 2> 0
            <Timespan 0 9> 1
            <Timespan 1 1> 2
            <Timespan 2 3> 3
            <Timespan 3 4> 4
            <Timespan 4 9> 5
            <Timespan 5 6> 6
            <Timespan 5 8> 7
            <Timespan 6 8> 8
            <Timespan 7 7> 9

        ::

            >>> tree.index(stream.timespans.Timespan(-100, 100))
            Traceback (most recent call last):
            ValueError: <Timespan -100 100> not in timespan collection.

        '''
        if not hasattr(timespan, 'startOffset') or \
            not hasattr(timespan, 'stopOffset'):
            message = 'Must have startOffset and stopOffset.'
            raise TimespanCollectionException(message)
        node = self._search(self._rootNode, timespan.startOffset)
        if node is None or timespan not in node.payload:
            raise ValueError('{} not in timespan collection.'.format(timespan))
        index = node.payload.index(timespan) + node.nodeStartIndex
        return index

    def insert(self, timespans):
        r'''
        Inserts `timespans` into this offset-tree.

        TODO: remove asserts...
        '''
        if hasattr(timespans, 'startOffset') and \
            hasattr(timespans, 'stopOffset'):
            timespans = [timespans]
        for timespan in timespans:
            assert hasattr(timespan, 'startOffset'), timespan
            assert hasattr(timespan, 'stopOffset'), timespan
            self._rootNode = self._insert(self._rootNode, timespan.startOffset)
            node = self._search(self._rootNode, timespan.startOffset)
            node.payload.append(timespan)
            node.payload.sort(key=lambda x: x.stopOffset)
        self._updateIndices(self._rootNode)
        self._updateOffsets(self._rootNode)

    def iterateConsonanceBoundedVerticalities(self):
        r'''
        Iterates consonant-bounded verticality subsequences in this
        offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for subsequence in tree.iterateConsonanceBoundedVerticalities():
            ...     print 'Subequence:'
            ...     for verticality in subsequence:
            ...         print '\t[{}] {}: {} [{}]'.format(
            ...             verticality.measureNumber,
            ...             verticality,
            ...             verticality.isConsonant,
            ...             verticality.beatStrength,
            ...             )
            ...
            Subequence:
                [2] <Verticality 6.0 {E3 E4 G#4 B4}>: True [0.25]
                [2] <Verticality 6.5 {E3 D4 G#4 B4}>: False [0.125]
                [2] <Verticality 7.0 {A2 C#4 E4 A4}>: True [0.5]
            Subequence:
                [3] <Verticality 9.0 {F#3 C#4 F#4 A4}>: True [1.0]
                [3] <Verticality 9.5 {B2 D4 G#4 B4}>: False [0.125]
                [3] <Verticality 10.0 {C#3 C#4 E#4 G#4}>: True [0.25]
            Subequence:
                [3] <Verticality 10.0 {C#3 C#4 E#4 G#4}>: True [0.25]
                [3] <Verticality 10.5 {C#3 B3 E#4 G#4}>: False [0.125]
                [3] <Verticality 11.0 {F#2 A3 C#4 F#4}>: True [0.5]
            Subequence:
                [3] <Verticality 12.0 {F#3 C#4 F#4 A4}>: True [0.25]
                [4] <Verticality 13.0 {G#3 B3 F#4 B4}>: False [1.0]
                [4] <Verticality 13.5 {F#3 B3 F#4 B4}>: False [0.125]
                [4] <Verticality 14.0 {G#3 B3 E4 B4}>: True [0.25]
            Subequence:
                [4] <Verticality 14.0 {G#3 B3 E4 B4}>: True [0.25]
                [4] <Verticality 14.5 {A3 B3 E4 B4}>: False [0.125]
                [4] <Verticality 15.0 {B3 D#4 F#4}>: True [0.5]
            Subequence:
                [4] <Verticality 15.0 {B3 D#4 F#4}>: True [0.5]
                [4] <Verticality 15.5 {B2 A3 D#4 F#4}>: False [0.125]
                [4] <Verticality 16.0 {C#3 G#3 C#4 E4}>: True [0.25]
            Subequence:
                [5] <Verticality 17.5 {F#3 D4 F#4 A4}>: True [0.125]
                [5] <Verticality 18.0 {G#3 C#4 E4 B4}>: False [0.25]
                [5] <Verticality 18.5 {G#3 B3 E4 B4}>: True [0.125]
            Subequence:
                [6] <Verticality 24.0 {F#3 C#4 F#4 A4}>: True [0.25]
                [7] <Verticality 25.0 {B2 D4 F#4 G#4}>: False [1.0]
                [7] <Verticality 25.5 {C#3 C#4 E#4 G#4}>: True [0.125]
            Subequence:
                [7] <Verticality 25.5 {C#3 C#4 E#4 G#4}>: True [0.125]
                [7] <Verticality 26.0 {D3 C#4 F#4}>: False [0.25]
                [7] <Verticality 26.5 {D3 F#3 B3 F#4}>: True [0.125]
            Subequence:
                [8] <Verticality 29.0 {A#2 F#3 C#4 F#4}>: True [1.0]
                [8] <Verticality 29.5 {A#2 F#3 D4 F#4}>: False [0.125]
                [8] <Verticality 30.0 {A#2 C#4 E4 F#4}>: False [0.25]
                [8] <Verticality 31.0 {B2 C#4 E4 F#4}>: False [0.5]
                [8] <Verticality 32.0 {C#3 B3 D4 F#4}>: False [0.25]
                [8] <Verticality 32.5 {C#3 A#3 C#4 F#4}>: False [0.125]
                [9] <Verticality 33.0 {D3 B3 F#4}>: True [1.0]
            Subequence:
                [9] <Verticality 33.0 {D3 B3 F#4}>: True [1.0]
                [9] <Verticality 33.5 {D3 B3 C#4 F#4}>: False [0.125]
                [9] <Verticality 34.0 {B2 B3 D4 F#4}>: True [0.25]
            Subequence:
                [9] <Verticality 34.0 {B2 B3 D4 F#4}>: True [0.25]
                [9] <Verticality 34.5 {B2 B3 D4 E#4}>: False [0.125]
                [9] <Verticality 35.0 {F#3 A#3 C#4 F#4}>: True [0.5]

        '''
        iterator = self.iterateVerticalities()
        startingVerticality = iterator.next()
        while not startingVerticality.isConsonant:
            startingVerticality = iterator.next()
        verticalityBuffer = [startingVerticality]
        for verticality in iterator:
            verticalityBuffer.append(verticality)
            if verticality.isConsonant:
                if 2 < len(verticalityBuffer):
                    yield tuple(verticalityBuffer)
                verticalityBuffer = [verticality]

    def iterateVerticalities(
        self,
        reverse=False,
        ):
        r'''
        Iterates all vertical moments in this offset-tree.

        ..  note:: The offset-tree can be mutated while its verticalities are
            iterated over. Each verticality holds a reference back to the
            offset-tree and will ask for the start-offset after (or before) its
            own start offset in order to determine the next verticality to
            yield. If you mutate the tree by adding or deleting timespans, the
            next verticality will reflect those changes.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> iterator = tree.iterateVerticalities()
            >>> for _ in range(10):
            ...     iterator.next()
            ...
            <Verticality 0.0 {A3 E4 C#5}>
            <Verticality 0.5 {G#3 B3 E4 B4}>
            <Verticality 1.0 {F#3 C#4 F#4 A4}>
            <Verticality 2.0 {G#3 B3 E4 B4}>
            <Verticality 3.0 {A3 E4 C#5}>
            <Verticality 4.0 {G#3 B3 E4 E5}>
            <Verticality 5.0 {A3 E4 C#5}>
            <Verticality 5.5 {C#3 E4 A4 C#5}>
            <Verticality 6.0 {E3 E4 G#4 B4}>
            <Verticality 6.5 {E3 D4 G#4 B4}>

        Verticalities can also be iterated in reverse:

            >>> iterator = tree.iterateVerticalities(reverse=True)
            >>> for _ in range(10):
            ...     iterator.next()
            ...
            <Verticality 35.0 {F#3 A#3 C#4 F#4}>
            <Verticality 34.5 {B2 B3 D4 E#4}>
            <Verticality 34.0 {B2 B3 D4 F#4}>
            <Verticality 33.5 {D3 B3 C#4 F#4}>
            <Verticality 33.0 {D3 B3 F#4}>
            <Verticality 32.5 {C#3 A#3 C#4 F#4}>
            <Verticality 32.0 {C#3 B3 D4 F#4}>
            <Verticality 31.0 {B2 C#4 E4 F#4}>
            <Verticality 30.0 {A#2 C#4 E4 F#4}>
            <Verticality 29.5 {A#2 F#3 D4 F#4}>

        '''
        if reverse:
            startOffset = self.latestStartOffset
            verticality = self.getVerticalityAt(startOffset)
            yield verticality
            verticality = verticality.previousVerticality
            while verticality is not None:
                yield verticality
                verticality = verticality.previousVerticality
        else:
            startOffset = self.earliestStartOffset
            verticality = self.getVerticalityAt(startOffset)
            yield verticality
            verticality = verticality.nextVerticality
            while verticality is not None:
                yield verticality
                verticality = verticality.nextVerticality

    def iterateVerticalitiesNwise(
        self,
        n=3,
        reverse=False,
        ):
        r'''
        Iterates verticalities in groups of length `n`.

        ..  note:: The offset-tree can be mutated while its verticalities are
            iterated over. Each verticality holds a reference back to the
            offset-tree and will ask for the start-offset after (or before) its
            own start offset in order to determine the next verticality to
            yield. If you mutate the tree by adding or deleting timespans, the
            next verticality will reflect those changes.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> iterator = tree.iterateVerticalitiesNwise(n=2)
            >>> for _ in range(4):
            ...     print iterator.next()
            ...
            <VerticalitySequence: [
                <Verticality 0.0 {A3 E4 C#5}>,
                <Verticality 0.5 {G#3 B3 E4 B4}>
                ]>
            <VerticalitySequence: [
                <Verticality 0.5 {G#3 B3 E4 B4}>,
                <Verticality 1.0 {F#3 C#4 F#4 A4}>
                ]>
            <VerticalitySequence: [
                <Verticality 1.0 {F#3 C#4 F#4 A4}>,
                <Verticality 2.0 {G#3 B3 E4 B4}>
                ]>
            <VerticalitySequence: [
                <Verticality 2.0 {G#3 B3 E4 B4}>,
                <Verticality 3.0 {A3 E4 C#5}>
                ]>

        Grouped verticalities can also be iterated in reverse:

        ::

            >>> iterator = tree.iterateVerticalitiesNwise(n=2, reverse=True)
            >>> for _ in range(4):
            ...     print iterator.next()
            ...
            <VerticalitySequence: [
                <Verticality 34.5 {B2 B3 D4 E#4}>,
                <Verticality 35.0 {F#3 A#3 C#4 F#4}>
                ]>
            <VerticalitySequence: [
                <Verticality 34.0 {B2 B3 D4 F#4}>,
                <Verticality 34.5 {B2 B3 D4 E#4}>
                ]>
            <VerticalitySequence: [
                <Verticality 33.5 {D3 B3 C#4 F#4}>,
                <Verticality 34.0 {B2 B3 D4 F#4}>
                ]>
            <VerticalitySequence: [
                <Verticality 33.0 {D3 B3 F#4}>,
                <Verticality 33.5 {D3 B3 C#4 F#4}>
                ]>


        TODO: remove assert
        '''
        n = int(n)
        assert 0 < n
        if reverse:
            for verticality in self.iterateVerticalities(reverse=True):
                verticalities = [verticality]
                while len(verticalities) < n:
                    nextVerticality = verticalities[-1].nextVerticality
                    if nextVerticality is None:
                        break
                    verticalities.append(nextVerticality)
                if len(verticalities) == n:
                    yield VerticalitySequence(verticalities)
        else:
            for verticality in self.iterateVerticalities():
                verticalities = [verticality]
                while len(verticalities) < n:
                    previousVerticality = verticalities[-1].previousVerticality
                    if previousVerticality is None:
                        break
                    verticalities.append(previousVerticality)
                if len(verticalities) == n:
                    yield VerticalitySequence(reversed(verticalities))

    def remove(self, timespans):
        r'''
        Removes `timespans` from this offset-tree.

        TODO: remove assert

        '''
        if hasattr(timespans, 'startOffset') and \
            hasattr(timespans, 'stopOffset'):
            timespans = [timespans]
        for timespan in timespans:
            assert hasattr(timespan, 'startOffset'), timespan
            assert hasattr(timespan, 'stopOffset'), timespan
            node = self._search(self._rootNode, timespan.startOffset)
            if node is None:
                return
            if timespan in node.payload:
                node.payload.remove(timespan)
            if not node.payload:
                self._rootNode = self._remove(self._rootNode, timespan.startOffset)
        self._updateIndices(self._rootNode)
        self._updateOffsets(self._rootNode)

    def splitAt(self, offsets):
        r'''
        Splits all timespans in this offset-tree at `offsets`, operating in
        place.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.findTimespansStartingAt(0.1)
            ()

        ::

            >>> for timespan in tree.findTimespansOverlapping(0.1):
            ...     timespan
            ...
            <ElementTimespan 0.0:0.5 <music21.note.Note C#>>
            <ElementTimespan 0.0:0.5 <music21.note.Note A>>
            <ElementTimespan 0.0:0.5 <music21.note.Note A>>
            <ElementTimespan 0.0:1.0 <music21.note.Note E>>

        ::

            >>> tree.splitAt(0.1)
            >>> for timespan in tree.findTimespansStartingAt(0.1):
            ...     timespan
            ...
            <ElementTimespan 0.1:0.5 <music21.note.Note C#>>
            <ElementTimespan 0.1:0.5 <music21.note.Note A>>
            <ElementTimespan 0.1:0.5 <music21.note.Note A>>
            <ElementTimespan 0.1:1.0 <music21.note.Note E>>

        ::

            >>> tree.findTimespansOverlapping(0.1)
            ()

        '''
        if not isinstance(offsets, collections.Iterable):
            offsets = [offsets]
        for offset in offsets:
            overlaps = self.findTimespansOverlapping(offset)
            if not overlaps:
                continue
            for overlap in overlaps:
                self.remove(overlap)
                shards = overlap.splitAt(offset)
                self.insert(shards)

    def toChordifiedScore(self):
        r'''
        Creates a score from the ElementTimespan objects stored in this offset-tree.

        A "template" score may be used to provide measure and time-signature
        information.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> chordifiedScore = tree.toChordifiedScore()
            >>> chordifiedScore.show('text')
            {0.0} <music21.stream.Measure 0 offset=0.0>
                {0.0} <music21.clef.TrebleClef>
                {0.0} <music21.key.KeySignature of 3 sharps, mode minor>
                {0.0} <music21.meter.TimeSignature 4/4>
                {0.0} <music21.chord.Chord A3 E4 C#5>
                {0.5} <music21.chord.Chord G#3 B3 E4 B4>
            {1.0} <music21.stream.Measure 1 offset=1.0>
                {0.0} <music21.chord.Chord F#3 C#4 F#4 A4>
                {1.0} <music21.chord.Chord G#3 B3 E4 B4>
                {2.0} <music21.chord.Chord A3 E4 C#5>
                {3.0} <music21.chord.Chord G#3 B3 E4 E5>
            {5.0} <music21.stream.Measure 2 offset=5.0>
                {0.0} <music21.chord.Chord A3 E4 C#5>
                {0.5} <music21.chord.Chord C#3 E4 A4 C#5>
                {1.0} <music21.chord.Chord E3 E4 G#4 B4>
                {1.5} <music21.chord.Chord E3 D4 G#4 B4>
                {2.0} <music21.chord.Chord A2 C#4 E4 A4>
                {3.0} <music21.chord.Chord E#3 C#4 G#4 C#5>
            {9.0} <music21.stream.Measure 3 offset=9.0>
                {0.0} <music21.layout.SystemLayout>
                {0.0} <music21.chord.Chord F#3 C#4 F#4 A4>
                {0.5} <music21.chord.Chord B2 D4 G#4 B4>
                {1.0} <music21.chord.Chord C#3 C#4 E#4 G#4>
                {1.5} <music21.chord.Chord C#3 B3 E#4 G#4>
                {2.0} <music21.chord.Chord F#2 A3 C#4 F#4>
                {3.0} <music21.chord.Chord F#3 C#4 F#4 A4>
            ...

        TODO: remove assert

        '''

        from music21 import stream
        sourceScore = self.sourceScore
        if isinstance(sourceScore, stream.Stream):
            templateOffsets = sorted(sourceScore.measureOffsetMap())
            templateOffsets.append(sourceScore.duration.quarterLength)
            if hasattr(sourceScore, 'parts') and len(sourceScore.parts) > 0:
                templateScore = sourceScore.parts[0].measureTemplate(
                    fillWithRests=False)
            else:
                templateScore = sourceScore.measureTemplate(
                    fillWithRests=False)
            tree = self.copy()
            tree.splitAt(templateOffsets)
            measureIndex = 0
            allOffsets = tree.allOffsets + tuple(templateOffsets)
            allOffsets = sorted(set(allOffsets))
            for startOffset, stopOffset in zip(allOffsets, allOffsets[1:]):
                while templateOffsets[1] <= startOffset:
                    templateOffsets.pop(0)
                    measureIndex += 1
                verticality = self.getVerticalityAt(startOffset)
                quarterLength = stopOffset - startOffset
                assert 0 < quarterLength, verticality
                element = makeElement(verticality, quarterLength)
                templateScore[measureIndex].append(element)
            return templateScore
        else:
            allOffsets = self.allOffsets
            elements = []
            for startOffset, stopOffset in zip(allOffsets, allOffsets[1:]):
                verticality = self.getVerticalityAt(startOffset)
                quarterLength = stopOffset - startOffset
                assert 0 < quarterLength, verticality
                element = makeElement(verticality, quarterLength)
                elements.append(element)
            score = stream.Score()
            for element in elements:
                score.append(element)
            return score

    def toPartwiseTimespanCollections(self):
        partwiseTimespanCollections = {}
        for part in self.allParts:
            partwiseTimespanCollections[part] = TimespanCollection()
        for elementTimespan in self:
            partwiseTimespanCollection = partwiseTimespanCollections[elementTimespan.part]
            partwiseTimespanCollection.insert(elementTimespan)
        return partwiseTimespanCollections

    def toPartwiseScore(self, templateScore=None):
        from music21 import stream
        sourceScore = self.sourceScore
        templateOffsets = sorted(sourceScore.measureOffsetMap())
        templateOffsets.append(sourceScore.duration.quarterLength)
        if hasattr(sourceScore, 'parts') and len(sourceScore.parts) > 0:
            templateScore = sourceScore.parts[0].measureTemplate(
                fillWithRests=False)
        else:
            templateScore = sourceScore.measureTemplate(
                fillWithRests=False)
        partMapping = collections.OrderedDict()
        outputScore = stream.Score()
        for part in self.allParts:
            newPart = stream.Part()
            for measure in templateScore:
                newMeasure = copy.deepcopy(measure)
                newPart.insert(measure.offset, newMeasure)
            partMapping[part] = newPart
            outputScore.append(newPart)

        treeMapping = self.toPartwiseTimespanCollections()
        for tree in treeMapping.values():
            #assert tree.maximumOverlap == 1
            silenceTimespans = []
            previousOffset = 0
            for timespan in tree:
                if timespan.startOffset != previousOffset:
                    silenceTimespan = ElementTimespan(
                        startOffset=previousOffset,
                        stopOffset=timespan.startOffset,
                        )
                    silenceTimespans.append(silenceTimespan)
                previousOffset = timespan.stopOffset
            if previousOffset != max(templateOffsets):
                silenceTimespan = ElementTimespan(
                    startOffset=previousOffset,
                    stopOffset=max(templateOffsets),
                    )
                silenceTimespans.append(silenceTimespan)
            tree.insert(silenceTimespans)
            tree.splitAt(templateOffsets)

        for oldPart in partMapping:
            tree = treeMapping[oldPart]
            part = partMapping[oldPart]
            for timespan in treeMapping[oldPart]:
                startOffset = timespan.startOffset
                stopOffset = timespan.stopOffset
                quarterLength = stopOffset - startOffset
                assert 0 < quarterLength, timespan
                if timespan.element is not None:
                    pitches = timespan.pitches
                    if len(pitches) == 1:
                        element = note.Note(pitches[0])
                    elif 1 < len(pitches):
                        element = chord.Chord(sorted(pitches))
                    else:
                        raise Exception('How did we get here?')
                else:
                    element = note.Rest()
                element.quarterLength = quarterLength
                measureIndex = bisect.bisect(templateOffsets, startOffset) - 1
                measureOffset = templateOffsets[measureIndex]
                measure = part[measureIndex]
                measureInternalOffset = startOffset - measureOffset
                measure.insert(measureInternalOffset, element)
            clef = part.bestClef(allowTreble8vb=True)
            part.insert(0, clef)

        return outputScore

    @staticmethod
    def unwrapVerticalities(verticalities):
        r'''
        Unwraps a sequence of `Verticality` objects into a dictionary of
        `Part`:`Horizontality` key/value pairs.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> iterator = tree.iterateVerticalitiesNwise()
            >>> verticalities = iterator.next()
            >>> unwrapped = tree.unwrapVerticalities(verticalities)
            >>> for part in sorted(unwrapped,
            ...     key=lambda x: x.getInstrument().partName,
            ...     ):
            ...     print part
            ...     horizontality = unwrapped[part]
            ...     for timespan in horizontality:
            ...         print '\t', timespan
            ...
            <music21.stream.Part Alto>
                <ElementTimespan 0.0:1.0 <music21.note.Note E>>
                <ElementTimespan 1.0:2.0 <music21.note.Note F#>>
            <music21.stream.Part Bass>
                <ElementTimespan 0.0:0.5 <music21.note.Note A>>
                <ElementTimespan 0.5:1.0 <music21.note.Note G#>>
                <ElementTimespan 1.0:2.0 <music21.note.Note F#>>
            <music21.stream.Part Soprano>
                <ElementTimespan 0.0:0.5 <music21.note.Note C#>>
                <ElementTimespan 0.5:1.0 <music21.note.Note B>>
                <ElementTimespan 1.0:2.0 <music21.note.Note A>>
            <music21.stream.Part Tenor>
                <ElementTimespan 0.0:0.5 <music21.note.Note A>>
                <ElementTimespan 0.5:1.0 <music21.note.Note B>>
                <ElementTimespan 1.0:2.0 <music21.note.Note C#>>

        '''
        unwrapped = {}
        for timespan in verticalities[0].overlapTimespans:
            if timespan.part not in unwrapped:
                unwrapped[timespan.part] = []
            unwrapped[timespan.part].append(timespan)
        for timespan in verticalities[0].startTimespans:
            if timespan.part not in unwrapped:
                unwrapped[timespan.part] = []
            unwrapped[timespan.part].append(timespan)
        for verticality in verticalities[1:]:
            for timespan in verticality.startTimespans:
                if timespan.part not in unwrapped:
                    unwrapped[timespan.part] = []
                unwrapped[timespan.part].append(timespan)
        for part, unused_timespans in unwrapped.items():
            unwrapped[part] = Horizontality(timespans=unwrapped[part])
        return unwrapped

    ### PUBLIC PROPERTIES ###

    @property
    def allOffsets(self):
        r'''
        Gets all unique offsets (both starting and stopping) of all timespans
        in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for offset in tree.allOffsets[:10]:
            ...     offset
            ...
            0.0
            0.5
            1.0
            2.0
            3.0
            4.0
            5.0
            5.5
            6.0
            6.5

        '''
        def recurse(node):
            result = set()
            if node is not None:
                if node.leftChild is not None:
                    result.update(recurse(node.leftChild))
                result.add(node.startOffset)
                result.add(node.stopOffsetLow)
                result.add(node.stopOffsetHigh)
                if node.rightChild is not None:
                    result.update(recurse(node.rightChild))
            return result
        return tuple(sorted(recurse(self._rootNode)))

    @property
    def allParts(self):
        parts = set()
        for timespan in self:
            parts.add(timespan.part)
        parts = sorted(parts, key=lambda x: x.getInstrument().partId)
        return parts

    @property
    def allStartOffsets(self):
        r'''
        Gets all unique start offsets of all timespans in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for offset in tree.allStartOffsets[:10]:
            ...     offset
            ...
            0.0
            0.5
            1.0
            2.0
            3.0
            4.0
            5.0
            5.5
            6.0
            6.5

        '''
        def recurse(node):
            result = []
            if node is not None:
                if node.leftChild is not None:
                    result.extend(recurse(node.leftChild))
                result.append(node.startOffset)
                if node.rightChild is not None:
                    result.extend(recurse(node.rightChild))
            return result
        return tuple(recurse(self._rootNode))

    @property
    def allStopOffsets(self):
        r'''
        Gets all unique stop offsets of all timespans in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> for offset in tree.allStopOffsets[:10]:
            ...     offset
            ...
            0.5
            1.0
            2.0
            4.0
            5.5
            6.0
            7.0
            8.0
            9.5
            10.5

        '''
        def recurse(node):
            result = set()
            if node is not None:
                if node.leftChild is not None:
                    result.update(recurse(node.leftChild))
                result.add(node.stopOffsetLow)
                result.add(node.stopOffsetHigh)
                if node.rightChild is not None:
                    result.update(recurse(node.rightChild))
            return result
        return tuple(sorted(recurse(self._rootNode)))

    @property
    def earliestStartOffset(self):
        r'''
        Gets the earlies start offset in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.earliestStartOffset
            0.0

        '''
        def recurse(node):
            if node.leftChild is not None:
                return recurse(node.leftChild)
            return node.startOffset
        return recurse(self._rootNode)

    @property
    def earliestStopOffset(self):
        r'''
        Gets the earliest stop offset in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.earliestStopOffset
            0.5

        '''
        return self._rootNode.stopOffsetLow

    @property
    def latestStartOffset(self):
        r'''
        Gets the lateset start offset in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.latestStartOffset
            35.0

        '''
        def recurse(node):
            if node.rightChild is not None:
                return recurse(node._rightChild)
            return node.startOffset
        return recurse(self._rootNode)

    @property
    def latestStopOffset(self):
        r'''
        Gets the latest stop offset in this offset-tree.

        ::

            >>> score = corpus.parse('bwv66.6')
            >>> tree = stream.timespans.TimespanCollection(score)
            >>> tree.latestStopOffset
            36.0

        '''
        return self._rootNode.stopOffsetHigh

    @property
    def maximumOverlap(self):
        overlap = None
        for verticality in self.iterateVerticalities():
            degreeOfOverlap = verticality.degreeOfOverlap
            if overlap is None:
                overlap = degreeOfOverlap
            elif overlap < degreeOfOverlap:
                overlap = degreeOfOverlap
        return overlap

    @property
    def minimumOverlap(self):
        overlap = None
        for verticality in self.iterateVerticalities():
            degreeOfOverlap = verticality.degreeOfOverlap
            if overlap is None:
                overlap = degreeOfOverlap
            elif degreeOfOverlap < overlap:
                overlap = degreeOfOverlap
        return overlap

    @property
    def sourceScore(self):
        return self._sourceScore


#------------------------------------------------------------------------------


class TimespanCollectionException(exceptions21.Music21Exception):
    pass

#------------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def testTimespanCollection(self):

        for attempt in range(100):
            starts = range(20)
            stops = range(20)
            random.shuffle(starts)
            random.shuffle(stops)
            timespans = [Timespan(start, stop)
                for start, stop in zip(starts, stops)
                ]
            tree = TimespanCollection()

            for i, timespan in enumerate(timespans):
                tree.insert(timespan)
                current_timespans_in_list = list(sorted(timespans[:i + 1],
                    key=lambda x: (x.startOffset, x.stopOffset)))
                current_timespans_in_tree = [x for x in tree]
                assert current_timespans_in_tree == current_timespans_in_list, \
                    (attempt, current_timespans_in_tree, current_timespans_in_list)
                assert tree._rootNode.stopOffsetLow == \
                    min(x.stopOffset for x in current_timespans_in_list)
                assert tree._rootNode.stopOffsetHigh == \
                    max(x.stopOffset for x in current_timespans_in_list)
                for i in range(len(current_timespans_in_tree)):
                    assert current_timespans_in_list[i] == \
                        current_timespans_in_tree[i]

            random.shuffle(timespans)
            while timespans:
                timespan = timespans.pop()
                current_timespans_in_list = sorted(timespans,
                    key=lambda x: (x.startOffset, x.stopOffset))
                tree.remove(timespan)
                current_timespans_in_tree = [x for x in tree]
                assert current_timespans_in_tree == current_timespans_in_list, \
                    (attempt, current_timespans_in_tree, current_timespans_in_list)
                if tree._rootNode is not None:
                    assert tree._rootNode.stopOffsetLow == \
                        min(x.stopOffset for x in current_timespans_in_list)
                    assert tree._rootNode.stopOffsetHigh == \
                        max(x.stopOffset for x in current_timespans_in_list)
                    for i in range(len(current_timespans_in_tree)):
                        assert current_timespans_in_list[i] == \
                            current_timespans_in_tree[i]


#------------------------------------------------------------------------------


_DOC_ORDER = (
    TimespanCollection,
    Verticality,
    Horizontality,
    Timespan,
    ElementTimespan,
    )


#------------------------------------------------------------------------------


if __name__ == "__main__":
    import music21
    music21.mainTest(Test)
