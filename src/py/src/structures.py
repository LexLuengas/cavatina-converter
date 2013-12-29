

#--- STRUCTURES ---#

import re

class InvalidSymbolError(Exception):
    pass

def MatchIndex(regexpr,array):
    for i in range(len(array)): # returns index of the first entry which matches regexpr, or *None* if it wasn't matched
        if re.match(regexpr,array[i]):
            return i
    return None

class TimeInterval(object):
    def __init__(self, length_exponent=0):
        self.length_exponent = length_exponent
        self.length_base = 1 # by 1/8
        self.denominator = 8
        self.set_length_exponent(self.length_exponent)

    def set_length_exponent(self, length_exponent):
        self.length_exponent = length_exponent
        self.length = self.length_base * (2 ** self.length_exponent)

    def increase_length_exponent(self):
        self.set_length_exponent(self.length_exponent + 1)

    def add_dot_length(self):
        if self.length_base * (2 ** self.length_exponent) > 1:
            self.length = 3 * self.length_base * (2 ** (self.length_exponent-1))
        else:
            self.denominator = 2 * self.denominator
            self.length = 3 * self.length_base * (2 ** self.length_exponent)

class Note(TimeInterval):
    def __init__(self, pitch, key_signature, length_exponent=0):
        self.pitch = pitch
        self.key_signature = key_signature
        super( Note,self ).__init__(length_exponent)
        self.set_pitch(self.pitch)
        
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
        if pitch >= note_range_size:
            self.length_base = 2
        self.pitch = pitch % note_range_size
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
        
        # ornamentation
        elif (mark == operators['inverter'] and MatchIndex('^[\[|\{]$', self.note_diacritics) != None): # inversion
            lastOrnmIndex = [i for i in self.note_diacritics if i in ornaments_symbols][-1] # last index of simple ornament
            self.note_diacritics[lastOrnmIndex] = self.note_diacritics[lastOrnmIndex] + '`'
        elif (mark == '[' and MatchIndex('\[+', self.note_diacritics) != None): # trills
            mark_index = MatchIndex('\[+', self.note_diacritics)
            self.note_diacritics[mark_index] = self.note_diacritics[mark_index] + '['
        elif mark in ornaments_symbols: # base case
            self.note_diacritics.append(mark)

    def get_name(self):
        note_accidentals = [accidentals_short[d] for d in self.note_diacritics if d in accidentals_short]
        note_articulations = [articulations[d] for d in self.note_diacritics if d in articulations]
        note_ornaments = [ornaments[d] for d in self.note_diacritics if d in ornaments]
        if accent_mark in self.note_diacritics:
            note_articulations.append('accent')
        
        return "{}{}{} [{}/{}]{}{}".format(
            self.name, ", ".join(note_accidentals), self.octave, self.length, self.denominator,
            
            ((", " + ", ".join(note_articulations)) if len(note_articulations) > 0 else ""),
            ((", " + ", ".join(note_ornaments)) if len(note_ornaments) > 0 else "")
            )

class Chord(object):
    def __init__(self, notes): # a list of Note objects
        self.notes = notes
        self.arpeggio = False

    def add_arpeggio(self):
        self.arpeggio = True

    def get_str(self):
        notes = '; '.join([note.get_name() for note in self.notes])
        if self.arpeggio:
            return "chord [arpeggio]({})".format(notes)
        else:
            return "chord ({})".format(notes)

class Rest(TimeInterval):
    def get_str(self):
        return "(rest [{}/{}])".format(self.length,self.denominator)
        

class Splitter(object):
    def __init__(self, length):
        self.length = length

    def get_str(self):
        return "space ({}/4)".format(self.length)

class MeasureEnd(object):
    def get_str(self):
        return "(measure end)"

class SectionEnd(object):
    def get_str(self):
        return "(section end)"

class End(object):
    def get_str(self):
        return "(end)"

class RepeatFrom(object):
    def get_str(self):
        return "||:"

class RepeatTo(object):
    def get_str(self):
        return ":||"

class RepeatSectionStart(object):
    def __init__(self, n):
        self.n = n
    
    def get_str(self):
        return "({}th repeat section start)".format(self.n)

class RepeatSectionEnd(object):
    def get_str(self):
        return "(repeat section end)"
        
class KeySignature(object):
    def __init__(self, clef, signature=0): # signature: an integer in the interval [-7,7]
        self.clef = clef
        
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

    def get_str(self):
        return "(clef {}, {} {})".format(self.clef, self.amount, self.sharps_or_flats)

class TimeSignature(object):
    def __init__(self, numerator, denominator):
        self.numerator = numerator
        self.denominator = denominator

    def get_str(self):
        return "(timesig {} / {})".format(self.numerator, self.denominator)

class Dynamic(object):
    def __init__(self, dynamic):
        self.dynamic = dynamic

    def get_str(self):
        return "(dynamic: {})".format(self.dynamic)

class GradualDynamic(object):
    def __init__(self, gdynamic):
        self.gdynamic = gdynamic

    def get_str(self):
        return "(change dynamic: {})".format(self.gdynamic)

class OctavationStart(object):
    def get_str(self):
        return "(8va)---{"

class OctavationEnd(object):
    def get_str(self):
        return "}(8va)"

class Segno(object):
    def get_str(self):
        return "(segno)"

class Coda(object):
    def get_str(self):
        return "(coda)"

class FromTo(object):
    def __init__(self, varfrom,varto=None):
        self.varfrom = varfrom
        self.varto = varto

    def get_str(self):
        return "({}".format(self.varfrom) + (" {})".format(self.varto) if self.varto != None else ")")

class PedalDown(object):
    def get_str(self):
        return '(pedal down)'

class PedalUp(object):
    def get_str(self):
        return '(pedal up)'

class Newline(object):
    def get_str(self):
        return '(newline)'

class ErrorSign(object):
    def get_str(self):
        return '(error symbol)'
