
import re
from .symbols import *
from .semantics import *

class InvalidSymbolError(Exception):
    pass

def MatchIndex(regexpr,array):
    for i in range(len(array)): # returns index of the first entry which matches regexpr, or *None* if it wasn't matched
        if re.match(regexpr,array[i]):
            return i
    return None

class TimeInterval(object):
    def __init__(self, length_exponent=0, denominator=8):
        self.length_exponent = length_exponent
        self.denominator = denominator
        self.set_length_exponent(self.length_exponent)

    def set_length_exponent(self, length_exponent):
        self.length_exponent = length_exponent
        self.length = 2 ** self.length_exponent

    def increase_length_exponent(self):
        self.set_length_exponent(self.length_exponent + 1)

    def add_dot_length(self):
        if 2 ** self.length_exponent > 1:
            self.length = 3 * (2 ** (self.length_exponent - 1))
        else:
            self.denominator = 2 * self.denominator
            self.length = 3 * (2 ** self.length_exponent)
    
    def get_quarterLength(self):
        return (float(self.length) / self.denominator) * 4

class Note(TimeInterval):
    def __init__(self, pitch, key_signature, length_exponent=0, denominator=8):
        self.pitch = pitch
        self.stem_direction = 'up' if note_range[self.pitch] in 'zxcvbnmasdfghZXCVBNMASDFGH' else 'down'
        self.key_signature = key_signature
        self.set_pitch(self.pitch)
        super(Note, self).__init__(length_exponent, denominator)
        
        self.note_diacritics = [] # list of strings containing all note alterations and note articulations as *input* symbols.
        
        signature_notes = self.key_signature.get_signature_notes()
        self.keyAccidental = False
        
        if self.name in signature_notes:
            self.keyAccidental = True # remember if added accidental comes from key signature
            if signature_notes[0] == 'F':
                self.add_diacritical_mark('=') # sostenido
            if signature_notes[0] == 'B':
                self.add_diacritical_mark('-') # bemol

    def set_pitch(self, pitch):
        self.pitch = pitch % eighth_note_range
        cases_name = { # conditional assignment
            'G' : scale[self.pitch % 7],
            'F' : scale[(self.pitch + 2) % 7],
            'C' : scale[(self.pitch + 1) % 7]
        }
        cases_octave = { # conditional assignment
            'G' : int(self.pitch / 7) + 3,
            'F' : int((self.pitch + 2) / 7) + 1,
            'C' : int((self.pitch + 1) / 7) + 2
        }
        self.name = cases_name[self.key_signature.get_clef()]
        self.octave = cases_octave[self.key_signature.get_clef()]
        
    def add_diacritical_mark(self, mark):
        # accidentals
        if (mark in accidentals_symbols and MatchIndex('^[-|=]$', self.note_diacritics) != None): #  double accidentals
            try: # if mark in self.note_diacritics
                mark_index = self.note_diacritics.index(mark)
                if not self.keyAccidental: # key signature consistency
                    self.note_diacritics[mark_index] = '--' if mark == '-' else '==' #...if mark == '='  
            except ValueError: # else
                if mark == '-':
                    if not self.keyAccidental:
                        self.note_diacritics[self.note_diacritics.index('=')] = '=-'
                    else:
                        self.note_diacritics[self.note_diacritics.index('=')] = '-'
                if mark == '=':
                    if not self.keyAccidental:
                        self.note_diacritics[self.note_diacritics.index('-')] = '-='
                    else:
                        self.note_diacritics[self.note_diacritics.index('-')] = '='
            self.keyAccidental = False
        elif (mark in accidentals_symbols and MatchIndex('[-|=][-|=]', self.note_diacritics) == None): # base case, do not exceed 2 diacritic maximum
            self.note_diacritics.append(mark)
        
        # articulations
        elif (mark in articulations_symbols and MatchIndex('^[\'|\"]$', self.note_diacritics) != None): #  double articulations
            try: # if mark in self.note_diacritics:
                mark_index = self.note_diacritics.index(mark)
                self.note_diacritics[mark_index] = '\'\'' if mark == '\'' else '\"\"' #...if mark == '\"'
            except ValueError: # else:
                pass
        elif (mark in articulations_symbols and MatchIndex('[\'\']|[\"\"]', self.note_diacritics) == None): # base case, do not exceed 2 diacritic maximum
            self.note_diacritics.append(mark)
        
        # accent
        elif mark == accent_mark:
            self.note_diacritics.append(mark)
            
        # tie
        elif mark == tie:
            self.note_diacritics.append(mark)
        
        # ornamentation
        elif (mark == operators['inverter'] and MatchIndex('^[\[|\{]$', self.note_diacritics) != None): # inversion
            lastOrnament = [i for i in self.note_diacritics if i in ornaments_symbols][-1] # last index of simple ornament
            lastOrnament = lastOrnament + '`'
        elif (mark == '[' and MatchIndex('\[+', self.note_diacritics) != None): # trills
            mark_index = MatchIndex('\[+', self.note_diacritics)
            self.note_diacritics[mark_index] = self.note_diacritics[mark_index] + '['
        elif mark in ornaments_symbols: # base case
            self.note_diacritics.append(mark)
    
    def invertStem(self):
        self.stem_direction = 'up' if self.stem_direction == 'down' else 'down'

    def __str__(self):
        note_accidentals = [accidentals_short[d] for d in self.note_diacritics if d in accidentals_short]
        note_articulations = [articulations[d] for d in self.note_diacritics if d in articulations]
        note_ornaments = [ornaments[d] for d in self.note_diacritics if d in ornaments]
        if accent_mark in self.note_diacritics:
            note_articulations.append('accent')
        if tie in self.note_diacritics:
            note_articulations.append('tie')
        
        return "{}{}{} [{}/{}]{}{}".format(
            self.name, ", ".join(note_accidentals), self.octave, self.length, self.denominator,
            
            ((", " + ", ".join(note_articulations)) if len(note_articulations) > 0 else ""),
            ((", " + ", ".join(note_ornaments)) if len(note_ornaments) > 0 else "")
            )
    
    def get_m21name(self):
        return self.name + str(self.octave)
        
    def get_m21accidental(self):
        accidentals_m21 = {
            '-' : 'flat',
            '=' : 'sharp',
            '--' : 'double-flat',
            '==' : 'double-sharp',
            '-=' : 'natural',
            '=-' : 'natural'
        }
        
        return next((accidentals_m21[x] for x in self.note_diacritics if x in accidentals_m21), None)
    
    def get_m21articulations(self):
        from music21 import articulations as m21articulations
        articulations_m21 = {
            '\'' : m21articulations.Staccato,
            '\"' : m21articulations.Tenuto,
            '\'\'' : m21articulations.Staccatissimo,
        }
        
        try:
            artic = [next((articulations_m21[x] for x in self.note_diacritics if x in articulations_m21))]
        except StopIteration:
            artic = []
        if accent_mark in self.note_diacritics:
            artic.append(m21articulations.Accent)
            
        return artic # a list of abstract music21.articulations classes
    
    def get_m21expressions(self):
        from music21 import expressions as m21expressions
        expressions_m21 = {
            '[' : m21expressions.Mordent,
            '{' : m21expressions.Turn,
            '[`' : m21expressions.InvertedMordent,
            '{`' : m21expressions.InvertedTurn,
            '[[' : m21expressions.Trill,
            '[[[' : m21expressions.Trill, # TODO: expressions.TrillExtension(<note.Note list>)
            '[[[[' : m21expressions.Trill, # span = 2 notes
            '[[[[[' : m21expressions.Trill, # span = 3 notes
            '[[[[[[' : m21expressions.Trill # span = 4 notes
        }
        
        try:
            expr = [next((expressions_m21[x] for x in self.note_diacritics if x in expressions_m21))]
        except StopIteration:
            expr = []
        if '\"\"' in self.note_diacritics:
            expr.append(m21expressions.Fermata)
            
        return expr
        
    def is_tied(self):
        return tie in self.note_diacritics

class Chord(object):
    def __init__(self, notes, beamed=False): # a list of Note objects
        self.notes = notes
        self.arpeggio = False
        self.beamToPrevious = beamed

    def add_arpeggio(self):
        self.arpeggio = True
    
    def __iter__(self):
        return iter(self.notes)
    
    def __len__(self):
        return len(self.notes)
    
    def __getitem__(self,i):
        return self.notes[i]

    def __str__(self):
        notes = '; '.join([str(note) for note in self.notes])
        if self.arpeggio:
            return "chord [arpeggio]({})".format(notes)
        else:
            return "chord ({})".format(notes)

class Rest(TimeInterval):
    def __str__(self):
        return "(rest [{}/{}])".format(self.length, self.denominator)

class Splitter(object):
    def __init__(self, length):
        self.length = length

    def __str__(self):
        return "space ({}/4)".format(self.length)

class MeasureEnd(object):
    def __str__(self):
        return "(measure end)"

class SectionEnd(object):
    def __str__(self):
        return "(section end)"

class End(object):
    def __str__(self):
        return "(end)"
        
class SystemicBarline(MeasureEnd):
    pass

class DoubleSystemicBarline(SectionEnd):
    pass
    
class BoldSystemicBarline(End):
    pass

class GrandStaff(object):
    def __str__(self):
        return "(grand staff)"

class RepeatFrom(object):
    def __str__(self):
        return "||:"

class RepeatTo(object):
    def __str__(self):
        return ":||"

class LongRepeatFrom(RepeatFrom):
    pass

class LongRepeatTo(RepeatTo):
    pass

class RepeatSectionStart(object):
    def __init__(self, n):
        self.n = n # string
    
    def __str__(self):
        return "({}th repeat section start)".format(self.n)
    
    def get_m21no(self):
        return self.n

class RepeatSectionEnd(object):
    def __str__(self):
        return "(repeat section end)"
        
class KeySignature(object):
    def __init__(self, clef, signature=0): # signature: an integer in the interval [-7,7]
        self.clef = clef
        self.signature = signature
        
        if signature > 0:
            self.sharps_or_flats = 'sharps'
        elif signature < 0:
            self.sharps_or_flats = 'flats'
        else:
            self.sharps_or_flats = 'sharps/flats'
            
        self.amount = abs(signature)
        
        if signature > 0:
            self.signature_notes = 'FCGDAEB'[:abs(signature)]
        elif signature <= 0:
            self.signature_notes = 'BEADGCF'[:abs(signature)]
    
    def get_clef(self):
        return self.clef
    
    def get_signature_notes(self):
        return self.signature_notes

    def __str__(self):
        return "(clef {}, {} {})".format(self.clef, self.amount, self.sharps_or_flats)
    
    def get_m21clef(self):
        from music21 import clef as m21clef
        m21clefs = {
            'G' : m21clef.TrebleClef,
            'F' : m21clef.BassClef,
            'C' : m21clef.AltoClef
        }
        
        return m21clefs[self.clef]
    
    def getm21signature(self):
        return self.signature

class TimeSignature(object):
    def __init__(self, numerator, denominator=None):
        self.numerator = numerator
        self.denominator = denominator
        self.c = None
        if not denominator:
            if numerator == 'c':
                self.c = numerator
                self.numerator = 4
                self.denominator = 4
            elif numerator == 'cut':
                self.c = numerator
                self.numerator = 2
                self.denominator = 2

    def __str__(self):
        return "(timesig {} / {})".format(self.numerator, self.denominator)
    
    def get_m21fractionalTime(self):
        if not self.c:
            return str(self.numerator) + '/' + str(self.denominator)
        else: # MusicXML does not yet support symbolized times, but it's been implemented
            return self.c

class Dynamic(object):
    def __init__(self, dynamic):
        self.dynamic = dynamic

    def __str__(self):
        return "(dynamic: {})".format(self.dynamic)
    
    def get_m21dynamic(self):
        return self.dynamic

class GradualDynamic(object):
    def __init__(self, gdynamic):
        self.gdynamic = gdynamic

    def __str__(self):
        return "(change dynamic: {})".format(self.gdynamic)
    
    def get_name(self):
        return self.gdynamic

class OctavationStart(object):
    def __init__(self, octaveTranspositions=1):
        self.octaveTranspositions = octaveTranspositions # for future integration of 'quindicesima'
        
    def __str__(self):
        if self.octaveTranspositions == 0:
            return "(8va)"
        else:
            return "(8va[{}x])---".format(self.octaveTranspositions) + "{"

class OctavationEnd(object):
    def __str__(self):
        return "}(8va)"

class Segno(object):
    def __str__(self):
        return "(segno)"

class Coda(object):
    def __str__(self):
        return "(coda)"

class FromTo(object):
    def __init__(self, varfrom, varto=None):
        self.varfrom = varfrom
        self.varto = varto

    def __str__(self):
        return "({}".format(self.varfrom) + (" {})".format(self.varto) if self.varto != None else ")")
    
    def get_m21parameters(self):
        return [self.varfrom, self.varto]

class PedalDown(object):
    def __str__(self):
        return '(pedal down)'

class PedalUp(object):
    def __str__(self):
        return '(pedal up)'

class Newline(object):
    def __str__(self):
        return '(newline)'

class ErrorSign(object):
    def __str__(self):
        return '(error symbol)'
