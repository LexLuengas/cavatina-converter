# -*- coding: utf-8 -*-
#-------------------------------------------------------------------------------
# Name:         converter.py
# Purpose:      Provide a common way to create Streams from any data music21
#               handles
#
# Authors:      Michael Scott Cuthbert
#               Christopher Ariza
#
# Copyright:    Copyright © 2009-2012 Michael Scott Cuthbert and the music21 Project
# License:      LGPL, see license.txt
#-------------------------------------------------------------------------------
'''
music21.converter contains tools for loading music from various file formats,
whether from disk, from the web, or from text, into
music21.stream.:class:`~music21.stream.Score` objects (or
other similar stream objects).


The most powerful and easy to use tool is the :func:`~music21.converter.parse`
function. Simply provide a filename, URL, or text string and, if the format
is supported, a :class:`~music21.stream.Score` will be returned.


This is the most general public interface for all formats.  Programmers
adding their own formats to the system should provide an interface here to
their own parsers (such as humdrum, musicxml, etc.)


The second and subsequent times that a file is loaded it will likely be much
faster since we store a parsed version of each file as a "pickle" object in
the temp folder on the disk.



>>> #_DOCS_SHOW s = converter.parse('d:/mydocs/schubert.krn')
>>> s = converter.parse(humdrum.testFiles.schubert) #_DOCS_HIDE
>>> s
<music21.stream.Score ...>
'''


import unittest

import copy
import os
import re
import urllib
import zipfile

# import StringIO # this module is not supported in python3
# use io.StringIO  in python 3, avail in 2.6, not 2.5

from music21 import abcFormat
from music21 import exceptions21
from music21 import common
from music21 import humdrum
from music21 import stream
from music21 import tinyNotation

from music21.capella import fromCapellaXML

from music21 import musedata as musedataModule
from music21.musedata import translate as musedataTranslate

from music21.musicxml import xmlHandler as musicxmlHandler


from music21 import romanText as romanTextModule
from music21.romanText import translate as romanTextTranslate

from music21.noteworthy import binaryTranslate as noteworthyBinary # @UnresolvedImport
from music21.noteworthy import translate as noteworthyTranslate

from music21 import environment
_MOD = 'converter.py'
environLocal = environment.Environment(_MOD)





#-------------------------------------------------------------------------------
class ArchiveManagerException(exceptions21.Music21Exception):
    pass

class PickleFilterException(exceptions21.Music21Exception):
    pass

class ConverterException(exceptions21.Music21Exception):
    pass

class ConverterFileException(exceptions21.Music21Exception):
    pass


#-------------------------------------------------------------------------------
class ArchiveManager(object):
    '''Before opening a file path, this class can check if this is an archived file collection, such as a .zip or or .mxl file. This will return the data from the archive.
    '''
    # for info on mxl files, see
    # http://www.recordare.com/xml/compressed-mxl.html

    def __init__(self, fp, archiveType='zip'):
        '''Only archive type supported now is zip.
        '''
        self.fp = fp
        self.archiveType = archiveType

    def isArchive(self):
        '''Return True or False if the filepath is an archive of the supplied archiveType.
        '''
        if self.archiveType == 'zip':
            # some .md files can be zipped
            if self.fp.endswith('mxl') or self.fp.endswith('md'):
                # try to open it, as some mxl files are not zips
                try:
                    unused = zipfile.ZipFile(self.fp, 'r')
                except zipfile.BadZipfile:
                    return False
                return True
            elif self.fp.endswith('zip'):
                return True
        else:
            raise ArchiveManagerException('no support for archiveType: %s' % self.archiveType)
        return False


    def getNames(self):
        '''Return a list of all names contained in this archive.
        '''
        post = []
        if self.archiveType == 'zip':
            f = zipfile.ZipFile(self.fp, 'r')
            for subFp in f.namelist():
                post.append(subFp)
            f.close()
        return post


    def getData(self, name=None, dataFormat='musicxml' ):
        '''Return data from the archive by name. If no name is given, a default may be available.

        For 'musedata' format this will be a list of strings. For 'musicxml' this will be a single string.
        '''
        if self.archiveType == 'zip':
            f = zipfile.ZipFile(self.fp, 'r')
            if name == None and dataFormat == 'musicxml': # try to auto-harvest
                # will return data as a string
                # note that we need to read the META-INF/container.xml file
                # and get the rootfile full-path
                # a common presentation will be like this:
                # ['musicXML.xml', 'META-INF/', 'META-INF/container.xml']
                for subFp in f.namelist():
                    # the name musicXML.xml is often used, or get top level
                    # xml file
                    if 'META-INF' in subFp:
                        continue
                    if subFp.endswith('.xml'):
                        post = f.read(subFp)
                        break

            elif name == None and dataFormat == 'musedata':
                # this might concatenate all parts into a single string
                # or, return a list of strings
                # alternative, a different method might return one at a time
                mdd = musedataModule.MuseDataDirectory(f.namelist())
                #environLocal.printDebug(['mdd object, namelist', mdd, f.namelist])

                post = []
                for subFp in mdd.getPaths():
                    component = f.open(subFp, 'rU')
                    lines = component.readlines()
                    #environLocal.printDebug(['subFp', subFp, len(lines)])
                    post.append(''.join(lines))

                    # note: the following methods do not properly employ
                    # universal new lines; this is a python problem:
                    # http://bugs.python.org/issue6759
                    #post.append(component.read())
                    #post.append(f.read(subFp, 'U'))
                    #msg.append('\n/END\n')

            f.close()
        else:
            raise ArchiveManagerException('no support for extension: %s' % self.archiveType)

        return post


#-------------------------------------------------------------------------------
class PickleFilter(object):
    '''
    Before opening a file path, this class checks to see if there is an up-to-date
    version of the file pickled and stored in the scratch directory.
    
    If the user has not specified a scratch directory, or if forceSource is True
    then a pickle path will not be created.
    '''
    def __init__(self, fp, forceSource=False, number=None):
        '''Provide a file path to check if there is pickled version.

        If forceSource is True, pickled files, if available, will not be
        returned.
        '''
        self.fp = fp
        self.forceSource = forceSource
        self.number = number
        #environLocal.printDebug(['creating pickle filter'])

    def _getPickleFp(self, directory, zipType=None):
        if directory == None:
            raise ValueError
        if zipType is None:
            extension = '.p'
        else:
            extension = '.pgz'
        
        if self.number is None:
            return os.path.join(directory, 'm21-' + common.getMd5(self.fp) + extension)
        else:
            return os.path.join(directory, 'm21-' + common.getMd5(self.fp) + '-' + str(self.number) + extension)

    def status(self):
        '''
        Given a file path specified with __init__, look for an up to date pickled 
        version of this file path. If it exists, return its fp, otherwise return the 
        original file path.

        Return arguments are file path to load, boolean whether to write a pickle, and 
        the file path of the pickle.
        
        Does not check that fp exists or create the pickle file.
        
        >>> fp = '/Users/Cuthbert/Desktop/musicFile.mxl'
        >>> pickfilt = converter.PickleFilter(fp)
        >>> #_DOCS_SHOW pickfilt.status()
        ('/Users/Cuthbert/Desktop/musicFile.mxl', True, '/var/folders/x5/rymq2tx16lqbpytwb1n_cc4c0000gn/T/music21/m21-18b8c5a5f07826bd67ea0f20462f0b8d.pgz')

        '''
        fpScratch = environLocal.getRootTempDir()
        m21Format = common.findFormatFile(self.fp)

        if m21Format == 'pickle': # do not pickle a pickle
            if self.forceSource:
                raise PickleFilterException('cannot access source file when only given a file path to a pickled file.')
            writePickle = False # cannot write pickle if no scratch dir
            fpLoad = self.fp
            fpPickle = None
        elif fpScratch == None or self.forceSource:
            writePickle = False # cannot write pickle if no scratch dir
            fpLoad = self.fp
            fpPickle = None
        else: # see which is more up to date
            fpPickle = self._getPickleFp(fpScratch, zipType='gz')
            if not os.path.exists(fpPickle):
                writePickle = True # if pickled file does not exist
                fpLoad = self.fp
            else:
                post = common.sortFilesRecent([self.fp, fpPickle])
                if post[0] == fpPickle: # pickle is most recent
                    writePickle = False
                    fpLoad = fpPickle
                elif post[0] == self.fp: # file is most recent
                    writePickle = True
                    fpLoad = self.fp
        return fpLoad, writePickle, fpPickle



#-------------------------------------------------------------------------------
# Converters are associated classes; they are not subclasses, but most define a pareData() method, a parseFile() method, and a .stream attribute or property.


#-------------------------------------------------------------------------------
class ConverterHumdrum(object):
    '''Simple class wrapper for parsing Humdrum data provided in a file or in a string.
    '''

    def __init__(self):
        self.stream = None

    #---------------------------------------------------------------------------
    def parseData(self, humdrumString, number=None):
        '''Open Humdrum data from a string

        >>> humdata = '**kern\\n*M2/4\\n=1\\n24r\\n24g#\\n24f#\\n24e\\n24c#\\n24f\\n24r\\n24dn\\n24e-\\n24gn\\n24e-\\n24dn\\n*-'
        >>> c = converter.ConverterHumdrum()
        >>> s = c.parseData(humdata)
        '''
        self.data = humdrum.parseData(humdrumString)
        #self.data.stream.makeNotation()

        self.stream = self.data.stream
        return self.data

    def parseFile(self, filepath, number=None):
        '''Open Humdram data from a file path.'''
        self.data = humdrum.parseFile(filepath)
        #self.data.stream.makeNotation()

        self.stream = self.data.stream
        return self.data

#-------------------------------------------------------------------------------
class ConverterTinyNotation(object):
    '''Simple class wrapper for parsing TinyNotation data provided in a file or in a string.
    '''

    def __init__(self):
        self.stream = None

    #---------------------------------------------------------------------------
    def parseData(self, tnData, number=None):
        '''Open TinyNotation data from a string or list

        >>> tnData = ["E4 r f# g=lastG trip{b-8 a g} c", "3/4"]
        >>> c = converter.ConverterTinyNotation()
        >>> s = c.parseData(tnData)
        '''
        if common.isStr(tnData):
            tnStr = tnData
            tnTs = None
        else: # assume a 2 element sequence
            tnStr = tnData[0]
            tnTs = tnData[1]
        self.stream = tinyNotation.TinyNotationStream(tnStr, tnTs)

    def parseFile(self, fp, number=None):
        '''Open TinyNotation data from a file path.'''

        f = open(fp)
        tnStr = f.read()
        f.close()
        self.stream = tinyNotation.TinyNotationStream(tnStr)

class ConverterNoteworthy(object):
    '''
    Simple class wrapper for parsing NoteworthyComposer data provided in a file or in a string.

    Gets data with the file format .nwctxt

    Users should not need this routine.  The basic format is


    >>> import os #_DOCS_HIDE
    >>> nwcTranslatePath = common.getSourceFilePath() + os.path.sep + 'noteworthy'
    >>> paertPath = nwcTranslatePath + os.path.sep + 'Part_OWeisheit.nwctxt' #_DOCS_HIDE
    >>> #_DOCS_SHOW paertPath = converter.parse('d:/desktop/arvo_part_o_weisheit.nwctxt')
    >>> paertStream = converter.parse(paertPath)
    >>> len(paertStream.parts)
    4

    For developers: see the documentation for :meth:`parseData` and :meth:`parseFile`
    to see the low-level usage.
    '''

    def __init__(self):
        self.stream = None

    #---------------------------------------------------------------------------
    def parseData(self, nwcData):
        r'''Open Noteworthy data from a string or list

        >>> nwcData = "!NoteWorthyComposer(2.0)\n|AddStaff\n|Clef|Type:Treble\n|Note|Dur:Whole|Pos:1^"
        >>> c = converter.ConverterNoteworthy()
        >>> c.parseData(nwcData)
        >>> c.stream.show('text')
        {0.0} <music21.stream.Part ...>
            {0.0} <music21.stream.Measure 0 offset=0.0>
                {0.0} <music21.clef.TrebleClef>
                {0.0} <music21.note.Note C>
        '''
        self.stream = noteworthyTranslate.NoteworthyTranslator().parseString(nwcData)


    def parseFile(self, fp, number=None):
        '''
        Open Noteworthy data (as nwctxt) from a file path.


        >>> import os #_DOCS_HIDE
        >>> nwcTranslatePath = common.getSourceFilePath() + os.path.sep + 'noteworthy'
        >>> filePath = nwcTranslatePath + os.path.sep + 'Part_OWeisheit.nwctxt' #_DOCS_HIDE
        >>> #_DOCS_SHOW paertPath = converter.parse('d:/desktop/arvo_part_o_weisheit.nwctxt')
        >>> c = converter.ConverterNoteworthy()
        >>> c.parseFile(filePath)
        >>> #_DOCS_SHOW c.stream.show()
        '''
        self.stream = noteworthyTranslate.NoteworthyTranslator().parseFile(fp)

class ConverterNoteworthyBinary(object):
    '''
    Simple class wrapper for parsing NoteworthyComposer binary data provided in a file or in a string.

    Gets data with the file format .nwc

    Users should not need this routine.  Call converter.parse directly
    '''

    def __init__(self):
        self.stream = None

    #---------------------------------------------------------------------------
    def parseData(self, nwcData):
        self.stream = noteworthyBinary.NWCConverter().parseString(nwcData)


    def parseFile(self, fp, number=None):
        self.stream = noteworthyBinary.NWCConverter().parseFile(fp)

#-------------------------------------------------------------------------------
class ConverterMusicXML(object):
    '''Converter for MusicXML
    '''

    def __init__(self, forceSource):
        self._mxScore = None # store the musicxml object representation
        self._stream = stream.Score()
        self.forceSource = forceSource

    #---------------------------------------------------------------------------
    def partIdToNameDict(self):
        return self._mxScore.partIdToNameDict()

    def load(self):
        '''Load all parts from a MusicXML object representation.
        This determines the order parts are found in the stream
        '''
        #t = common.Timer()
        #t.start()
        from music21.musicxml import fromMxObjects
        fromMxObjects.mxScoreToScore(self._mxScore, inputM21 = self._stream)
        #self._stream._setMX(self._mxScore)
        #t.stop()
        #environLocal.printDebug(['music21 object creation time:', t])

    def _getStream(self):
        return self._stream

    stream = property(_getStream)


    #---------------------------------------------------------------------------
    def parseData(self, xmlString, number=None):
        '''Open MusicXML data from a string.'''
        c = musicxmlHandler.Document()
        c.read(xmlString)
        self._mxScore = c.score #  the mxScore object from the musicxml Document
        if len(self._mxScore) == 0:
            #print xmlString
            raise ConverterException('score from xmlString (%s...) either has no parts defined or was incompletely parsed' % xmlString[:30])
        self.load()

    def parseFile(self, fp, number=None):
        '''Open from a file path; check to see if there is a pickled
        version available and up to date; if so, open that, otherwise
        open source.
        '''
        # return fp to load, if pickle needs to be written, fp pickle
        # this should be able to work on a .mxl file, as all we are doing
        # here is seeing which is more recent

        pfObj = PickleFilter(fp, self.forceSource)
        # fpDst here is the file path to load, which may or may not be
        # a pickled file
        fpDst, writePickle, fpPickle = pfObj.status() # get status @UnusedVariable

        formatSrc = common.findFormatFile(fp)
        # here we determine if we have pickled file or a musicxml file
        m21Format = common.findFormatFile(fpDst)
        pickleError = False

        c = musicxmlHandler.Document()
        if m21Format == 'pickle':
            environLocal.printDebug(['opening pickled file', fpDst])
            try:
                c.openPickle(fpDst)
            except (ImportError, EOFError):
                msg = 'pickled file (%s) is damaged; a new file will be created.' % fpDst
                pickleError = True
                writePickle = True
                if formatSrc == 'musicxml':
                    #environLocal.printDebug([msg], environLocal)
                    fpDst = fp # set to orignal file path
                else:
                    raise ConverterException(msg)
            # check if this pickle is up to date
            if (hasattr(c.score, 'm21Version') and
                c.score.m21Version >= musicxmlHandler.musicxmlMod.VERSION_MINIMUM):
                pass
                #environLocal.printDebug(['pickled file version is compatible', c.score.m21Version])
            else:
                try:
                    environLocal.printDebug(['pickled file version is not compatible', c.score.m21Version])
                except (AttributeError, TypeError):
                    # some old pickles have no versions
                    pass
                pickleError = True
                writePickle = True
                fpDst = fp # set to orignal file path

        if m21Format == 'musicxml' or (formatSrc == 'musicxml' and pickleError):
            environLocal.printDebug(['opening musicxml file:', fpDst])

            # here, we can see if this is a mxl or similar archive
            arch = ArchiveManager(fpDst)
            if arch.isArchive():
                c.read(arch.getData())
            else: # its a file path or a raw musicxml string
                c.open(fpDst)

        # get mxScore object from .score attribute
        self._mxScore = c.score
        #print self._mxScore
        # check that we have parts
        if len(self._mxScore) == 0:
            raise ConverterException('score from file path (%s) no parts defined' % fp)

        # movement titles can be stored in more than one place in musicxml
        # manually insert file name as a title if no titles are defined
        if self._mxScore.get('movementTitle') == None:
            mxWork = self._mxScore.get('workObj')
            if mxWork == None or mxWork.get('workTitle') == None:
                junk, fn = os.path.split(fp)
                # set as movement title
                self._mxScore.set('movementTitle', fn)

        # only write pickle if we have parts defined
        if writePickle:
            pass
        #    if fpPickle == None: # if original file cannot be found
        #        raise ConverterException('attempting to write pickle but no file path is given')
        #    environLocal.printDebug(['writing pickled file', fpPickle])
        #    c.writePickle(fpPickle)

        self.load()




#-------------------------------------------------------------------------------
class ConverterMidi(object):
    '''
    Simple class wrapper for parsing MIDI.
    '''

    def __init__(self):
        # always create a score instance
        self._stream = stream.Score()

    def parseData(self, strData, number=None):
        '''
        Get MIDI data from a binary string representation.

        Calls midi.translate.midiStringToStream.
        '''
        from music21.midi import translate as midiTranslate
        self._stream = midiTranslate.midiStringToStream(strData)

    def parseFile(self, fp, number=None):
        '''
        Get MIDI data from a file path.

        Calls midi.translate.midiFilePathToStream.
        '''
        from music21.midi import translate as midiTranslate
        midiTranslate.midiFilePathToStream(fp, self._stream)

    def _getStream(self):
        return self._stream

    stream = property(_getStream)




#-------------------------------------------------------------------------------
class ConverterABC(object):
    '''
    Simple class wrapper for parsing ABC.
    '''

    def __init__(self):
        # always create a score instance
        self._stream = stream.Score()

    def parseData(self, strData, number=None):
        '''
        Get ABC data, as token list, from a string representation.
        If more than one work is defined in the ABC data, a
        :class:`~music21.stream.Opus` object will be returned;
        otherwise, a :class:`~music21.stream.Score` is returned.
        '''
        af = abcFormat.ABCFile()
        # do not need to call open or close
        abcHandler = af.readstr(strData, number=number)
        # set to stream
        if abcHandler.definesReferenceNumbers():
            # this creates an Opus object, not a Score object
            self._stream = abcFormat.translate.abcToStreamOpus(abcHandler,
                number=number)
        else: # just one work
            abcFormat.translate.abcToStreamScore(abcHandler, self._stream)

    def parseFile(self, fp, number=None):
        '''Get MIDI data from a file path. If more than one work is defined in the ABC data, a  :class:`~music21.stream.Opus` object will be returned; otherwise, a :class:`~music21.stream.Score` is returned.

        If `number` is provided, and this ABC file defines multiple works with a X: tag, just the specified work will be returned.
        '''
        #environLocal.printDebug(['ConverterABC.parseFile: got number', number])

        af = abcFormat.ABCFile()
        af.open(fp)
        # returns a handler instance of parse tokens
        abcHandler = af.read(number=number)
        af.close()

        # only create opus if multiple ref numbers
        # are defined; if a number is given an opus will no be created
        if abcHandler.definesReferenceNumbers():
            # this creates a Score or Opus object, depending on if a number
            # is given
            self._stream = abcFormat.translate.abcToStreamOpus(abcHandler,
                           number=number)
        # just get a single work
        else:
            abcFormat.translate.abcToStreamScore(abcHandler, self._stream)

    def _getStream(self):
        return self._stream

    stream = property(_getStream)


class ConverterRomanText(object):
    '''Simple class wrapper for parsing roman text harmonic definitions.
    '''

    def __init__(self):
        # always create a score instance
        self._stream = stream.Score()

    def parseData(self, strData, number=None):
        '''
        '''
        rtf = romanTextModule.RTFile()
        rtHandler = rtf.readstr(strData)
        if rtHandler.definesMovements():
            # this re-defines Score as an Opus
            self._stream = romanTextTranslate.romanTextToStreamOpus(rtHandler)
        else:
            romanTextTranslate.romanTextToStreamScore(rtHandler, self._stream)

    def parseFile(self, fp, number=None):
        '''
        '''
        rtf = romanTextModule.RTFile()
        rtf.open(fp)
        # returns a handler instance of parse tokens
        rtHandler = rtf.read()
        rtf.close()
        romanTextTranslate.romanTextToStreamScore(rtHandler, self._stream)

    def _getStream(self):
        return self._stream

    stream = property(_getStream)



class ConverterCapella(object):
    '''
    Simple class wrapper for parsing Capella .capx XML files.  See capella/fromCapellaXML.
    '''

    def __init__(self):
        self._stream = None

    def parseData(self, strData, number=None):
        '''
        parse a data stream of uncompessed capella xml

        N.B. for web parsing, it gets more complex.
        '''
        ci = fromCapellaXML.CapellaImporter()
        ci.parseXMLText(strData)
        scoreObj = ci.systemScoreFromScore(self.mainDom.documentElement)
        partScore = ci.partScoreFromSystemScore(scoreObj)
        self._stream = partScore
    def parseFile(self, fp, number=None):
        '''
        '''
        ci = fromCapellaXML.CapellaImporter()
        self._stream = ci.scoreFromFile(fp)

    def _getStream(self):
        return self._stream

    stream = property(_getStream)



#-------------------------------------------------------------------------------
class ConverterMuseData(object):
    '''Simple class wrapper for parsing MuseData.
    '''

    def __init__(self):
        # always create a score instance
        self._stream = stream.Score()

    def parseData(self, strData, number=None):
        '''Get musedata from a string representation.

        '''
        if common.isStr(strData):
            strDataList = [strData]
        else:
            strDataList = strData

        mdw = musedataModule.MuseDataWork()

        for strData in strDataList:
            mdw.addString(strData)

        musedataTranslate.museDataWorkToStreamScore(mdw, self._stream)


    def parseFile(self, fp, number=None):
        '''
        '''
        mdw = musedataModule.MuseDataWork()

        af = ArchiveManager(fp)

        #environLocal.printDebug(['ConverterMuseData: parseFile', fp, af.isArchive()])
        # for dealing with one or more files
        if fp.endswith('.zip') or af.isArchive():
            #environLocal.printDebug(['ConverterMuseData: found archive', fp])
            # get data will return all data from the zip as a single string
            for partStr in af.getData(dataFormat='musedata'):
                #environLocal.printDebug(['partStr', len(partStr)])
                mdw.addString(partStr)
        else:
            if os.path.isdir(fp):
                mdd = musedataModule.MuseDataDirectory(fp)
                fpList = mdd.getPaths()
            elif not common.isListLike(fp):
                fpList = [fp]
            else:
                fpList = fp

            for fp in fpList:
                mdw.addFile(fp)

        #environLocal.printDebug(['ConverterMuseData: mdw file count', len(mdw.files)])

        musedataTranslate.museDataWorkToStreamScore(mdw, self._stream)

    def _getStream(self):
        return self._stream

    stream = property(_getStream)

#-------------------------------------------------------------------------------
class Converter(object):
    '''
    A class used for converting all supported data formats into music21 objects.

    Not a subclass, but a wrapper for different converter objects based on format.
    '''
    _DOC_ATTR = {'subConverter': 'a ConverterXXX object that will do the actual converting.',}
    
    def __init__(self):
        self.subConverter = None
        self._thawedStream = None # a stream object unthawed

    def setSubconverterFromFormat(self, format, forceSource=False): # @ReservedAssignment
        '''
        sets the .subConverter according to the format of `format`:
        
        >>> convObj = converter.Converter()
        >>> convObj.setSubconverterFromFormat('humdrum')
        >>> convObj.subConverter
        <music21.converter.ConverterHumdrum object at 0x...>
        '''
        
        # assume for now that pickled files are always musicxml
        # this WILL change in the future
        if format is None:
            raise ConverterException('Did not find a format from the source file')

        if format in ['musicxml', 'pickle']:
            self.subConverter = ConverterMusicXML(forceSource=forceSource)
        elif format == 'midi':
            self.subConverter = ConverterMidi()
        elif format == 'humdrum':
            self.subConverter = ConverterHumdrum()
        elif format.lower() in ['tinynotation']:
            self.subConverter = ConverterTinyNotation()
        elif format == 'abc':
            self.subConverter = ConverterABC()
        elif format == 'musedata':
            self.subConverter = ConverterMuseData()
        elif format == 'noteworthytext':
            self.subConverter = ConverterNoteworthy()
        elif format == 'noteworthy':
            self.subConverter = ConverterNoteworthyBinary()
        elif format == 'capella':
            self.subConverter = ConverterCapella()

        elif format == 'text': # based on extension
            # presently, all text files are treated as roman text
            # may need to handle various text formats
            self.subConverter = ConverterRomanText()
        elif format.lower() in ['romantext', 'rntxt']:
            self.subConverter = ConverterRomanText()
        else:
            raise ConverterException('no such format: %s' % format)

    def _getDownloadFp(self, directory, ext, url):
        if directory == None:
            raise ValueError
        return os.path.join(directory, 'm21-' + common.getMd5(url) + ext)

    def parseFileNoPickle(self, fp, number=None, format=None, forceSource=False): # @ReservedAssignment
        '''
        Given a file path, parse and store a music21 Stream.

        If format is None then look up the format from the file
        extension using `common.findFormatFile`.
        
        Does not use or store pickles
        '''
        #environLocal.printDebug(['attempting to parseFile', fp])
        if not os.path.exists(fp):
            raise ConverterFileException('no such file eists: %s' % fp)
        useFormat = format

        if useFormat is None:
            # if the file path is to a directory, assume it is a collection of
            # musedata parts
            if os.path.isdir(fp):
                useFormat = 'musedata'
            else:
                useFormat = common.findFormatFile(fp)
                if useFormat is None:
                    raise ConverterFileException('cannot find a format extensions for: %s' % fp)
        self.setSubconverterFromFormat(useFormat, forceSource=forceSource)
        self.subConverter.parseFile(fp, number=number)
        self.stream.filePath = fp
        self.stream.fileNumber = number
        self.stream.fileFormat = useFormat
    
    def getFormatFromFileExtension(self, fp):
        '''
        gets the format from a file extension.
        '''
        
        # if the file path is to a directory, assume it is a collection of
        # musedata parts
        useFormat = None
        if os.path.isdir(fp):
            useFormat = 'musedata'
        else:
            useFormat = common.findFormatFile(fp)
            if useFormat is None:
                raise ConverterFileException('cannot find a format extensions for: %s' % fp)
        return useFormat
    
    def parseFile(self, fp, number=None, format=None, forceSource=False, storePickle=True): # @ReservedAssignment
        '''
        Given a file path, parse and store a music21 Stream.

        If format is None then look up the format from the file
        extension using `common.findFormatFile`.
        
        Will load from a pickle unless forceSource is True
        Will store as a pickle unless storePickle is False
        '''
        import freezeThaw
        if not os.path.exists(fp):
            raise ConverterFileException('no such file eists: %s' % fp)
        useFormat = format

        if useFormat is None:
            useFormat = self.getFormatFromFileExtension(fp)
        pfObj = PickleFilter(fp, forceSource, number)
        unused_fpDst, writePickle, fpPickle = pfObj.status()
        if writePickle is False and fpPickle is not None and forceSource is False:
            environLocal.printDebug("Loading Pickled version")
            try:
                self._thawedStream = thaw(fpPickle, zipType='zlib')
            except:
                environLocal.warn("Could not parse pickle, %s ...rewriting" % fpPickle)
                self.parseFileNoPickle(fp, number, format, forceSource)

            self.stream.filePath = fp
            self.stream.fileNumber = number
            self.stream.fileFormat = useFormat
        else:
            environLocal.printDebug("Loading original version")
            self.parseFileNoPickle(fp, number, format, forceSource)
            if writePickle is True and fpPickle is not None and storePickle is True:
                # save the stream to disk...
                environLocal.printDebug("Freezing Pickle")
                s = self.stream
                sf = freezeThaw.StreamFreezer(s, fastButUnsafe=True)
                sf.write(fp=fpPickle, zipType='zlib')
                
                environLocal.printDebug("Replacing self.stream")
                # get a new stream
                self._thawedStream = thaw(fpPickle, zipType='zlib')
                self.stream.filePath = fp
                self.stream.fileNumber = number
                self.stream.fileFormat = useFormat

            

    def parseData(self, dataStr, number=None, format=None, forceSource=False): # @ReservedAssignment
        '''
        Given raw data, determine format and parse into a music21 Stream.
        '''
        useFormat = format
        if common.isListLike(dataStr):
            useFormat = 'tinyNotation'
#         if type(dataStr) == unicode:
#             environLocal.printDebug(['Converter.parseData: got a unicode string'])

        # get from data in string if not specified
        if useFormat is None: # its a string
            dataStr = dataStr.lstrip()
            useFormat, dataStr = self.formatFromHeader(dataStr)

            if useFormat is not None:
                pass
            elif dataStr.startswith('<?xml') or dataStr.startswith('musicxml:'):
                useFormat = 'musicxml'
            elif dataStr.startswith('MThd') or dataStr.startswith('midi:'):
                useFormat = 'midi'
            elif dataStr.startswith('!!!') or dataStr.startswith('**') or dataStr.startswith('humdrum:'):
                useFormat = 'humdrum'
            elif dataStr.lower().startswith('tinynotation:'):
                useFormat = 'tinyNotation'

            # assume MuseData must define a meter and a key
            elif 'WK#:' in dataStr and 'measure' in dataStr:
                useFormat = 'musedata'
            elif 'M:' in dataStr and 'K:' in dataStr:
                useFormat = 'abc'
            elif 'Time Signature:' in dataStr and 'm1' in dataStr:
                useFormat = 'romanText'
            else:
                raise ConverterException('File not found or no such format found for: %s' % dataStr)

        self.setSubconverterFromFormat(useFormat)
        self.subConverter.parseData(dataStr, number=number)


    def parseURL(self, url, format=None, number=None): # @ReservedAssignment
        '''Given a url, download and parse the file
        into a music21 Stream stored in the `stream`
        property of the converter object.

        Note that this checks the user Environment
        `autoDownlaad` setting before downloading.

        TODO: replace with free version of jeanieLightBrownHair

        >>> #_DOCS_SHOW jeanieLightBrownURL = 'http://www.wikifonia.org/node/4391'
        >>> c = converter.Converter()
        >>> #_DOCS_SHOW c.parseURL(jeanieLightBrownURL)
        >>> #_DOCS_SHOW jeanieStream = c.stream
        '''
        autoDownload = environLocal['autoDownload']
        if autoDownload in ('deny', 'ask'):
            message = 'Automatic downloading of URLs is presently set to {!r};'
            message += ' configure your Environment "autoDownload" setting to '
            message += '"allow" to permit automatic downloading: '
            message += "environment.set('autoDownload', 'allow')"
            message = message.format(autoDownload)
            raise ConverterException(message)

        # If we give the URL to a Wikifonia main page,
        # redirect to musicxml page:
        matchedWikifonia = re.search("wikifonia.org/node/(\d+)", url)
        if matchedWikifonia:
            url = 'http://static.wikifonia.org/' + matchedWikifonia.group(1) + '/musicxml.xml'

        # this format check is here first to see if we can find the format
        # in the url; if forcing a format we do not need this
        # we do need the file extension to construct file path below
        if format is None:
            formatFromURL, ext = common.findFormatExtURL(url)
            if formatFromURL is None: # cannot figure out what it is
                raise ConverterException('cannot determine file format of url: %s' % url)
        else:
            unused_formatType, ext = common.findFormat(format)
            if ext is None:
                ext = '.txt'

        directory = environLocal.getRootTempDir()
        dst = self._getDownloadFp(directory, ext, url)
        if not os.path.exists(dst):
            try:
                environLocal.printDebug(['downloading to:', dst])
                fp, unused_headers = urllib.urlretrieve(url, filename=dst)
            except IOError:
                raise ConverterException('cannot access file: %s' % url)
        else:
            environLocal.printDebug(['using already downloaded file:', dst])
            fp = dst

        # update format based on downloaded fp
        if format is None: # if not provided as an argument
            useFormat = common.findFormatFile(fp)
        else:
            useFormat = format
        self.setSubconverterFromFormat(useFormat, forceSource=False)
        self.subConverter.parseFile(fp, number=number)
        self.stream.filePath = fp
        self.stream.fileNumber = number
        self.stream.fileFormat = useFormat


    validHeaderFormats = ['musicxml', 'midi', 'humdrum', 'tinyNotation', 'musedata', 'abc', 'romanText']

    def formatFromHeader(self, dataStr):
        '''
        if dataStr begins with a text header such as  "tinyNotation:" then
        return that format plus the dataStr with the head removed.

        Else, return (None, dataStr) where dataStr is the original untouched.

        Not case sensitive.

        >>> c = converter.Converter()
        >>> c.formatFromHeader('tinynotation: C4 E2')
        ('tinyNotation', 'C4 E2')

        >>> c.formatFromHeader('C4 E2')
        (None, 'C4 E2')
        '''

        dataStrStartLower = dataStr[:20].lower()

        foundFormat = None
        for possibleFormat in self.validHeaderFormats:
            if dataStrStartLower.startswith(possibleFormat.lower() + ':'):
                foundFormat = possibleFormat
                dataStr = dataStr[len(foundFormat) + 1:]
                dataStr = dataStr.lstrip()
                break
        return (foundFormat, dataStr)



    #---------------------------------------------------------------------------
    # properties

    def _getStream(self):
        '''
        Returns the .subConverter.stream object.
        '''
        if self._thawedStream is not None:
            return self._thawedStream
        elif self.subConverter is not None:
            return self.subConverter.stream
        else:
            return None
        # not _stream: please don't look in other objects' private variables;
        #              humdrum worked differently.

    stream = property(_getStream)




#-------------------------------------------------------------------------------
# module level convenience methods


def parseFile(fp, number=None, format=None, forceSource=False):  #@ReservedAssignment
    '''
    Given a file path, attempt to parse the file into a Stream.
    '''
    v = Converter()
    v.parseFile(fp, number=number, format=format, forceSource=forceSource)
    return v.stream

def parseData(dataStr, number=None, format=None): # @ReservedAssignment
    '''
    Given musical data represented within a Python string, attempt to parse the
    data into a Stream.
    '''
    v = Converter()
    v.parseData(dataStr, number=number, format=format)
    return v.stream

def parseURL(url, number=None, format=None, forceSource=False): # @ReservedAssignment
    '''
    Given a URL, attempt to download and parse the file into a Stream. Note:
    URL downloading will not happen automatically unless the user has set their
    Environment "autoDownload" preference to "allow".
    '''
    v = Converter()
    v.parseURL(url, format=format)
    return v.stream

def parse(value, *args, **keywords):
    '''
    Given a file path, encoded data in a Python string, or a URL, attempt to
    parse the item into a Stream.  Note: URL downloading will not happen
    automatically unless the user has set their Environment "autoDownload"
    preference to "allow".

    Keywords can include `number` which specifies a piece number in a file of
    multipiece file.

    `format` specifies the format to parse the line of text or the file as.

    A string of text is first checked to see if it is a filename that exists on
    disk.  If not it is searched to see if it looks like a URL.  If not it is
    processed as data.

    The data is normally interpreted as a line of TinyNotation with the first
    argument being the time signature:

    TODO: SHOW FILE
    TODO: SHOW URL

    >>> s = converter.parse("tinyNotation: 3/4 E4 r f# g=lastG trip{b-8 a g} c")
    >>> s.getElementsByClass(meter.TimeSignature)[0]
    <music21.meter.TimeSignature 3/4>

    >>> s2 = converter.parse("E8 f# g#' G f g# g G#", "2/4")
    >>> s2.show('text')
    {0.0} <music21.meter.TimeSignature 2/4>
    {0.0} <music21.note.Note E>
    {0.5} <music21.note.Note F#>
    {1.0} <music21.note.Note G#>
    {1.5} <music21.note.Note G>
    {2.0} <music21.note.Note F>
    {2.5} <music21.note.Note G#>
    {3.0} <music21.note.Note G>
    {3.5} <music21.note.Note G#>

    '''

    #environLocal.printDebug(['attempting to parse()', value])
    if 'forceSource' in keywords:
        forceSource = keywords['forceSource']
    else:
        forceSource = False

    # see if a work number is defined; for multi-work collections
    if 'number' in keywords:
        number = keywords['number']
    else:
        number = None

    if 'format' in keywords:
        m21Format = keywords['format']
    else:
        m21Format = None

    if (common.isListLike(value) and len(value) == 2 and
        value[1] == None and os.path.exists(value[0])):
        # comes from corpus.search
        return parseFile(value[0], format=m21Format)
    elif (common.isListLike(value) and len(value) == 2 and
        isinstance(value[1], int) and os.path.exists(value[0])):
        # corpus or other file with movement number
        return parseFile(value[0], format=m21Format).getScoreByNumber(value[1])
    elif common.isListLike(value) or len(args) > 0: # tiny notation list
        if len(args) > 0: # add additional args to a list
            value = [value] + list(args)
        return parseData(value, number=number)
    # a midi string, must come before os.path.exists test
    elif value.startswith('MThd'):
        return parseData(value, number=number, format=m21Format)
    elif os.path.exists(value):
        return parseFile(value, number=number, format=m21Format, forceSource=forceSource)
    elif (value.startswith('http://') or value.startswith('https://')):
        # its a url; may need to broaden these criteria
        return parseURL(value, number=number, format=m21Format, forceSource=forceSource)
    else:
        return parseData(value, number=number, format=m21Format)



def freeze(streamObj, fmt=None, fp=None, fastButUnsafe=False, zipType='zlib'):
    '''Given a StreamObject and a file path, serialize and store the Stream to a file.

    This function is based on the :class:`~music21.converter.StreamFreezer` object.

    The serialization format is defined by the `fmt` argument; 'pickle' (the default) is only one
    presently supported.  'json' or 'jsonnative' will be used once jsonpickle is good enough.

    If no file path is given, a temporary file is used.

    The file path is returned.


    >>> c = converter.parse('c4 d e f', '4/4')
    >>> c.show('text')
    {0.0} <music21.meter.TimeSignature 4/4>
    {0.0} <music21.note.Note C>
    {1.0} <music21.note.Note D>
    {2.0} <music21.note.Note E>
    {3.0} <music21.note.Note F>
    >>> fp = converter.freeze(c, fmt='pickle')
    >>> #_DOCS_SHOW fp
    '/tmp/music21/sjiwoe.pgz'

    The file can then be "thawed" back into a Stream using the :func:`~music21.converter.thaw` method.

    >>> d = converter.thaw(fp)
    >>> d.show('text')
    {0.0} <music21.meter.TimeSignature 4/4>
    {0.0} <music21.note.Note C>
    {1.0} <music21.note.Note D>
    {2.0} <music21.note.Note E>
    {3.0} <music21.note.Note F>
    '''
    from music21 import freezeThaw
    v = freezeThaw.StreamFreezer(streamObj, fastButUnsafe=fastButUnsafe)
    return v.write(fmt=fmt, fp=fp, zipType=zipType) # returns fp


def thaw(fp, zipType='zlib'):
    '''Given a file path of a serialized Stream, defrost the file into a Stream.

    This function is based on the :class:`~music21.converter.StreamFreezer` object.

    See the documentation for :meth:`~music21.converter.freeze` for demos.
    '''
    from music21 import freezeThaw
    v = freezeThaw.StreamThawer()
    v.open(fp, zipType=zipType)
    return v.stream


def freezeStr(streamObj, fmt=None):
    '''
    Given a StreamObject
    serialize and return a serialization string.

    This function is based on the
    :class:`~music21.converter.StreamFreezer` object.

    The serialization format is defined by
    the `fmt` argument; 'pickle' (the default),
    is the only one presently supported.


    >>> c = converter.parse('c4 d e f', '4/4')
    >>> c.show('text')
    {0.0} <music21.meter.TimeSignature 4/4>
    {0.0} <music21.note.Note C>
    {1.0} <music21.note.Note D>
    {2.0} <music21.note.Note E>
    {3.0} <music21.note.Note F>
    >>> data = converter.freezeStr(c, fmt='pickle')
    >>> len(data) > 20 # pickle implementation dependent
    True
    >>> d = converter.thawStr(data)
    >>> d.show('text')
    {0.0} <music21.meter.TimeSignature 4/4>
    {0.0} <music21.note.Note C>
    {1.0} <music21.note.Note D>
    {2.0} <music21.note.Note E>
    {3.0} <music21.note.Note F>

    '''
    from music21 import freezeThaw
    v = freezeThaw.StreamFreezer(streamObj)
    return v.writeStr(fmt=fmt) # returns a string

def thawStr(strData):
    '''
    Given a serialization string, defrost into a Stream.

    This function is based on the :class:`~music21.converter.StreamFreezer` object.
    '''
    from music21 import freezeThaw
    v = freezeThaw.StreamThawer()
    v.openStr(strData)
    return v.stream




#-------------------------------------------------------------------------------
class TestExternal(unittest.TestCase):
    # interpreter loading

    def runTest(self):
        pass

    def testMusicXMLConversion(self):
        from music21.musicxml import testFiles
        for mxString in testFiles.ALL: # @UndefinedVariable
            a = ConverterMusicXML(False)
            a.parseData(mxString)

    def testMusicXMLTabConversion(self):
        from music21.musicxml import testFiles
        mxString = testFiles.ALL[5] # @UndefinedVariable
        a = ConverterMusicXML(False)
        a.parseData(mxString)

    def testConversionMusicXml(self):
        c = stream.Score()

        from music21.musicxml import testPrimitive
        mxString = testPrimitive.chordsThreeNotesDuration21c
        a = parseData(mxString)

        mxString = testPrimitive.beams01
        b = parseData(mxString)
        #b.show()

        c.append(a[0])
        c.append(b[0])
        c.show()
        # TODO: this is only showing the minimum number of measures


    def testParseURL(self):
        urlB = 'http://kern.ccarh.org/cgi-bin/ksdata?l=users/craig/classical/schubert/piano/d0576&file=d0576-06.krn&f=kern'
        urlC = 'http://kern.ccarh.org/cgi-bin/ksdata?l=users/craig/classical/bach/cello&file=bwv1007-01.krn&f=xml'
        for url in [urlB, urlC]:
            try:
                unused_post = parseURL(url)
            except:
                print(url)
                raise

    def testFreezer(self):
        from music21 import corpus
        s = corpus.parse('bach/bwv66.6.xml')
        fp = freeze(s)
        s2 = thaw(fp)
        s2.show()


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def testCopyAndDeepcopy(self):
        '''Test copying all objects defined in this module
        '''
        import sys, types
        for part in sys.modules[self.__module__].__dict__:
            match = False
            for skip in ['_', '__', 'Test', 'Exception']:
                if part.startswith(skip) or part.endswith(skip):
                    match = True
            if match:
                continue
            obj = getattr(sys.modules[self.__module__], part)
            if callable(obj) and not isinstance(obj, types.FunctionType):
                i = copy.copy(obj)
                j = copy.deepcopy(obj)


    def testConversionMX(self):
        from music21.musicxml import testPrimitive
        from music21 import dynamics
        from music21 import note


        mxString = testPrimitive.pitches01a
        a = parse(mxString)
        a = a.flat
        b = a.getElementsByClass(note.Note)
        # there should be 102 notes
        self.assertEqual(len(b), 102)


        # test directions, dynamics, wedges
        mxString = testPrimitive.directions31a
        a = parse(mxString)
        a = a.flat
        b = a.getElementsByClass(dynamics.Dynamic)
        # there should be 27 dynamics found in this file
        self.assertEqual(len(b), 27)
        c = a.getElementsByClass(note.Note)
        self.assertEqual(len(c), 53)

        # two starts and two stops == 2!
        d = a.getElementsByClass(dynamics.DynamicWedge)
        self.assertEqual(len(d), 2)


        # test lyrics
        mxString = testPrimitive.lyricsMelisma61d
        a = parse(mxString)
        a = a.flat
        b = a.getElementsByClass(note.Note)
        found = []
        for noteObj in b:
            for obj in noteObj.lyrics:
                found.append(obj)
        self.assertEqual(len(found), 3)


        # test we are getting rests
        mxString = testPrimitive.restsDurations02a
        a = parse(mxString)
        a = a.flat
        b = a.getElementsByClass(note.Rest)
        self.assertEqual(len(b), 19)


        # test if we can get trills
        mxString = testPrimitive.notations32a
        a = parse(mxString)
        a = a.flat
        b = a.getElementsByClass(note.Note)



        mxString = testPrimitive.rhythmDurations03a
        a = parse(mxString)
        #a.show('t')
        self.assertEqual(len(a), 2) # one part, plus metadata
        for part in a.getElementsByClass(stream.Part):
            self.assertEqual(len(part), 7) # seven measures
            measures = part.getElementsByClass(stream.Measure)
            self.assertEqual(int(measures[0].number), 1)
            self.assertEqual(int(measures[-1].number), 7)

        # print a.recurseRepr()



        # print a.recurseRepr()

        # get the third movement
#         mxFile = corpus.getWork('opus18no1')[2]
#         a = parse(mxFile)
#         a = a.flat
#         b = a.getElementsByClass(dynamics.Dynamic)
#         # 110 dynamics
#         self.assertEqual(len(b), 110)
#
#         c = a.getElementsByClass(note.Note)
#         # over 1000 notes
#         self.assertEqual(len(c), 1289)



    def testConversionMXChords(self):
        from music21 import chord
        from music21.musicxml import testPrimitive

        mxString = testPrimitive.chordsThreeNotesDuration21c
        a = parse(mxString)
        for part in a.getElementsByClass(stream.Part):
            chords = part.flat.getElementsByClass(chord.Chord)
            self.assertEqual(len(chords), 7)
            knownSize = [3, 2, 3, 3, 3, 3, 3]
            for i in range(len(knownSize)):
                #print chords[i].pitches, len(chords[i].pitches)
                self.assertEqual(knownSize[i], len(chords[i].pitches))


    def testConversionMXBeams(self):

        from music21.musicxml import testPrimitive

        mxString = testPrimitive.beams01
        a = parse(mxString)
        part = a.parts[0]
        notes = part.flat.notesAndRests
        beams = []
        for n in notes:
            if "Note" in n.classes:
                beams += n.beams.beamsList
        self.assertEqual(len(beams), 152)


    def testConversionMXTime(self):

        from music21.musicxml import testPrimitive

        mxString = testPrimitive.timeSignatures11c
        a = parse(mxString)
        unused_part = a.parts[0]


        mxString = testPrimitive.timeSignatures11d
        a = parse(mxString)
        part = a.parts[0]

        notes = part.flat.notesAndRests
        self.assertEqual(len(notes), 11)


    def testConversionMXClefPrimitive(self):
        from music21 import clef
        from music21.musicxml import testPrimitive
        mxString = testPrimitive.clefs12a
        a = parse(mxString)
        part = a.parts[0]

        clefs = part.flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 18)


    def testConversionMXClefTimeCorpus(self):

        from music21 import corpus, clef, meter
        a = corpus.parse('luca')

        # there should be only one clef in each part
        clefs = a.parts[0].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)
        self.assertEqual(clefs[0].sign, 'G')

        # second part
        clefs = a.parts[1].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)
        self.assertEqual(clefs[0].octaveChange, -1)
        self.assertEqual(type(clefs[0]).__name__, 'Treble8vbClef')

        # third part
        clefs = a.parts[2].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)

        # check time signature count
        ts = a.parts[1].flat.getElementsByClass(meter.TimeSignature)
        self.assertEqual(len(ts), 4)


        a = corpus.parse('mozart/k156/movement4')

        # violin part
        clefs = a.parts[0].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)
        self.assertEqual(clefs[0].sign, 'G')

        # viola
        clefs = a.parts[2].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)
        self.assertEqual(clefs[0].sign, 'C')

        # violoncello
        clefs = a.parts[3].flat.getElementsByClass(clef.Clef)
        self.assertEqual(len(clefs), 1)
        self.assertEqual(clefs[0].sign, 'F')

        # check time signatures
        # there are
        ts = a.parts[0].flat.getElementsByClass(meter.TimeSignature)
        self.assertEqual(len(ts), 1)


    def testConversionMXArticulations(self):
        from music21 import note
        from music21.musicxml import testPrimitive
        from music21.musicxml import m21ToString

        mxString = testPrimitive.articulations01
        a = parse(mxString)
        part = a.parts[0]

        notes = part.flat.getElementsByClass(note.Note)
        self.assertEqual(len(notes), 4)
        post = []
        match = ["<class 'music21.articulations.Staccatissimo'>",
        "<class 'music21.articulations.Accent'>",
        "<class 'music21.articulations.Staccato'>",
        "<class 'music21.articulations.Tenuto'>"]
        for i in range(len(notes)):
            post.append(str(notes[i].articulations[0].__class__))
        self.assertEqual(post, match)

        # try to go the other way
        post = m21ToString.fromMusic21Object(a)
        #a.show()

    def testConversionMXKey(self):
        from music21 import key
        from music21.musicxml import testPrimitive
        mxString = testPrimitive.keySignatures13a
        a = parse(mxString)
        part = a.parts[0]

        keyList = part.flat.getElementsByClass(key.KeySignature)
        self.assertEqual(len(keyList), 46)


    def testConversionMXMetadata(self):
        from music21.musicxml import testFiles

        a = parse(testFiles.mozartTrioK581Excerpt) # @UndefinedVariable
        self.assertEqual(a.metadata.composer, 'Wolfgang Amadeus Mozart')
        self.assertEqual(a.metadata.title, 'Quintet for Clarinet and Strings')
        self.assertEqual(a.metadata.movementName, 'Menuetto (Excerpt from Second Trio)')

        a = parse(testFiles.binchoisMagnificat) # @UndefinedVariable
        self.assertEqual(a.metadata.composer, 'Gilles Binchois')
        # this gets the best title available, even though this is movement title
        self.assertEqual(a.metadata.title, 'Excerpt from Magnificat secundi toni')


    def testConversionMXBarlines(self):
        from music21 import bar
        from music21.musicxml import testPrimitive
        a = parse(testPrimitive.barlines46a)
        part = a.parts[0]
        barlineList = part.flat.getElementsByClass(bar.Barline)
        self.assertEqual(len(barlineList), 11)

    def testConversionXMLayout(self):

        from music21.musicxml import testPrimitive
        from music21 import stream, layout

        a = parse(testPrimitive.systemLayoutTwoPart)
        #a.show()

        part = a.getElementsByClass(stream.Part)[0]
        systemLayoutList = part.flat.getElementsByClass(layout.SystemLayout)
        measuresWithSL = []
        for e in systemLayoutList:
            measuresWithSL.append(e.measureNumber)
        self.assertEqual(measuresWithSL, [1, 3, 4, 5, 7, 8])
        self.assertEqual(len(systemLayoutList), 6)


    def testConversionMXTies(self):

        from music21.musicxml import testPrimitive
        from music21 import clef

        a = parse(testPrimitive.multiMeasureTies)
        #a.show()

        countTies = 0
        countStartTies = 0
        for p in a.parts:
            post = p.getClefs()[0]
            self.assertEqual(isinstance(post, clef.TenorClef), True)
            for n in p.flat.notes:
                if n.tie != None:
                    countTies += 1
                    if n.tie.type == 'start' or n.tie.type =='continue':
                        countStartTies += 1

        self.assertEqual(countTies, 57)
        self.assertEqual(countStartTies, 40)


    def testConversionMXInstrument(self):
        from music21 import corpus
        s = corpus.parse('beethoven/opus18no1/movement3.xml')
        #s.show()
        is1 = s.parts[0].flat.getElementsByClass('Instrument')
        self.assertEqual(len(is1), 1)
        is2 = s.parts[1].flat.getElementsByClass('Instrument')
        self.assertEqual(len(is2), 1)

        is3 = s.parts[2].flat.getElementsByClass('Instrument')
        self.assertEqual(len(is3), 1)

        is4 = s.parts[3].flat.getElementsByClass('Instrument')
        self.assertEqual(len(is4), 1)



    def testConversionMidiBasic(self):
        directory = common.getPackageDir(relative=False, remapSep=os.sep)
        for fp in directory:
            if fp.endswith('midi'):
                break

        dirLib = os.path.join(fp, 'testPrimitive')
        # a simple file created in athenacl
        fp = os.path.join(dirLib, 'test01.mid')

        unused_s = parseFile(fp)
        unused_s = parse(fp)

        c = ConverterMidi()
        c.parseFile(fp)

        # try low level string data passing
        f = open(fp, 'rb')
        data = f.read()
        f.close()

        c.parseData(data)

        # try module-leve; function
        parseData(data)
        parse(data)


    def testConversionMidiNotes(self):
        from music21 import meter, key, chord, note

        fp = os.path.join(common.getSourceFilePath(), 'midi', 'testPrimitive',  'test01.mid')
        # a simple file created in athenacl
        #for fn in ['test01.mid', 'test02.mid', 'test03.mid', 'test04.mid']:
        s = parseFile(fp)
        #s.show()
        self.assertEqual(len(s.flat.getElementsByClass(note.Note)), 18)


        # has chords and notes
        fp = os.path.join(common.getSourceFilePath(), 'midi', 'testPrimitive',  'test05.mid')
        s = parseFile(fp)
        #s.show()
        #environLocal.printDebug(['\nopening fp', fp])

        self.assertEqual(len(s.flat.getElementsByClass(note.Note)), 2)
        self.assertEqual(len(s.flat.getElementsByClass(chord.Chord)), 4)

        self.assertEqual(len(s.flat.getElementsByClass(meter.TimeSignature)), 0)
        self.assertEqual(len(s.flat.getElementsByClass(key.KeySignature)), 0)


        # this sample has eight note triplets
        fp = os.path.join(common.getSourceFilePath(), 'midi', 'testPrimitive',  'test06.mid')
        s = parseFile(fp)
        #s.show()

        #environLocal.printDebug(['\nopening fp', fp])

        #s.show()
        dList = [n.quarterLength for n in s.flat.notesAndRests[:30]]
        match = [0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 1.0, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.33333333333333331, 0.33333333333333331, 0.33333333333333331, 0.5, 0.5, 1.0]
        self.assertEqual(dList, match)


        self.assertEqual(len(s.flat.getElementsByClass('TimeSignature')), 1)
        self.assertEqual(len(s.flat.getElementsByClass('KeySignature')), 1)


        # this sample has sixteenth note triplets
        # TODO much work is still needed on getting timing right
        # this produces numerous errors in makeMeasure partitioning
        fp = os.path.join(common.getSourceFilePath(), 'midi', 'testPrimitive',  'test07.mid')
        #environLocal.printDebug(['\nopening fp', fp])
        s = parseFile(fp)
        #s.show('t')
        self.assertEqual(len(s.flat.getElementsByClass('TimeSignature')), 1)
        self.assertEqual(len(s.flat.getElementsByClass('KeySignature')), 1)




        # this sample has dynamic changes in key signature
        fp = os.path.join(common.getSourceFilePath(), 'midi', 'testPrimitive',  'test08.mid')
        #environLocal.printDebug(['\nopening fp', fp])
        s = parseFile(fp)
        #s.show('t')
        self.assertEqual(len(s.flat.getElementsByClass('TimeSignature')), 1)
        found = s.flat.getElementsByClass('KeySignature')
        self.assertEqual(len(found), 3)
        # test the right keys
        self.assertEqual(found[0].sharps, -3)
        self.assertEqual(found[1].sharps, 3)
        self.assertEqual(found[2].sharps, -1)


    def testConversionMXRepeats(self):
        from music21 import bar
        from music21.musicxml import testPrimitive

        mxString = testPrimitive.simpleRepeat45a
        s = parse(mxString)

        part = s.parts[0]
        measures = part.getElementsByClass('Measure')
        self.assertEqual(measures[0].leftBarline, None)
        self.assertEqual(measures[0].rightBarline.style, 'final')

        self.assertEqual(measures[1].leftBarline, None)
        self.assertEqual(measures[1].rightBarline.style, 'final')

        mxString = testPrimitive.repeatMultipleTimes45c
        s = parse(mxString)

        self.assertEqual(len(s.flat.getElementsByClass(bar.Barline)), 4)
        part = s.parts[0]
        measures = part.getElementsByClass('Measure')

        #s.show()



    def testConversionABCOpus(self):

        from music21.abcFormat import testFiles
        from music21 import corpus
        from music21 import stream

        s = parse(testFiles.theAleWifesDaughter)
        # get a Stream object, not an opus
        self.assertEqual(isinstance(s, stream.Score), True)
        self.assertEqual(isinstance(s, stream.Opus), False)
        self.assertEqual(len(s.flat.notesAndRests), 66)

        # a small essen collection
        op = corpus.parse('essenFolksong/teste')
        # get a Stream object, not an opus
        #self.assertEqual(isinstance(op, stream.Score), True)
        self.assertEqual(isinstance(op, stream.Opus), True)
        self.assertEqual([len(s.flat.notesAndRests) for s in op], [33, 51, 59, 33, 29, 174, 67, 88])
        #op.show()

        # get one work from the opus
        s = corpus.parse('essenFolksong/teste', number=6)
        self.assertEqual(isinstance(s, stream.Score), True)
        self.assertEqual(isinstance(s, stream.Opus), False)
        self.assertEqual(s.metadata.title, 'Moli hua')

        #s.show()


    def testConversionABCWorkFromOpus(self):
        # test giving a work number at loading
        from music21 import corpus
        s = corpus.parse('essenFolksong/han1', number=6)
        self.assertEqual(isinstance(s, stream.Score), True)
        self.assertEqual(s.metadata.title, 'Yi gan hongqi kongzhong piao')
        # make sure that beams are being made
        self.assertEqual(str(s.parts[0].flat.notesAndRests[4].beams), '<music21.beam.Beams <music21.beam.Beam 1/start>/<music21.beam.Beam 2/start>>')
        #s.show()



    def testConversionMusedata(self):

        from music21.musedata import testFiles

        cmd = ConverterMuseData()
        cmd.parseData(testFiles.bach_cantata5_mvmt3)
        unused_s = cmd.stream
        #s.show()

        # test data id
        s = parse(testFiles.bach_cantata5_mvmt3)
        self.assertEqual(s.metadata.title, 'Wo soll ich fliehen hin')
        self.assertEqual(len(s.parts), 3)


        fp = os.path.join(common.getSourceFilePath(), 'musedata', 'testZip.zip')
        s = parse(fp)
        self.assertEqual(len(s.parts), 4)
        #s.show()



    def testMixedArchiveHandling(self):
        '''Test getting data out of musedata or musicxml zip files.
        '''
        fp = os.path.join(common.getSourceFilePath(), 'musicxml', 'testMxl.mxl')
        af = ArchiveManager(fp)
        # for now, only support zip
        self.assertEqual(af.archiveType, 'zip')
        self.assertEqual(af.isArchive(), True)
        # if this is a musicxml file, there will only be single file; we
        # can cal get datat to get this
        post = af.getData()
        self.assertEqual(post[:38], '<?xml version="1.0" encoding="UTF-8"?>')
        self.assertEqual(af.getNames(), ['musicXML.xml', 'META-INF/', 'META-INF/container.xml'])

        # test from a file that ends in zip
        # note: this is a stage1 file!
        fp = os.path.join(common.getSourceFilePath(), 'musedata', 'testZip.zip')
        af = ArchiveManager(fp)
        # for now, only support zip
        self.assertEqual(af.archiveType, 'zip')
        self.assertEqual(af.isArchive(), True)
        self.assertEqual(af.getNames(), ['01/', '01/04', '01/02', '01/03', '01/01'] )

        # returns a list of strings
        self.assertEqual(af.getData(dataFormat='musedata')[0][:30], '378\n1080  1\nBach Gesells\nchaft')


        #mdw = musedataModule.MuseDataWork()
        # can add a list of strings from getData
        #mdw.addString(af.getData(dataFormat='musedata'))
        #self.assertEqual(len(mdw.files), 4)
#
#         mdpList = mdw.getParts()
#         self.assertEqual(len(mdpList), 4)

        # try to load parse the zip file
        #s = parse(fp)

        # test loading a directory
        fp = os.path.join(common.getSourceFilePath(), 'musedata',
                'testPrimitive', 'test01')
        cmd = ConverterMuseData()
        cmd.parseFile(fp)


#-------------------------------------------------------------------------------
# define presented order in documentation
_DOC_ORDER = [parse, parseFile, parseData, parseURL, freeze, thaw, freezeStr, thawStr, Converter, ConverterMusicXML, ConverterHumdrum]


if __name__ == "__main__":
    # sys.arg test options will be used in mainTest()
    import music21
    music21.mainTest(Test)



#------------------------------------------------------------------------------
# eof

