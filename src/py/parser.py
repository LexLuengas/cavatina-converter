# -*- coding: utf-8 -*-


#--- SEMANTICS ---#

scale = [
    'C', #'do'
    'D', #'re'
    'E', #'mi'
    'F', #'fa'
    'G', #'sol'
    'A', #'la'
    'B' #'si'
]

splitter_length = { # in quarters
    ' ' : 4,
    '/' : 2,
    '//' : 1
}

clefs = {
    '_' : 'G', #'sol'
    '+' : 'F', #'fa'
    '_+' : 'C', #'do'
    '+_' : 'C' #'do'
}

repetition = {
    'o' : 1,
    'oo' : 2,
    'o`' : 'end'
}

octavation = {
    'O' : 1,
    'OO' : 1,
    'O`' : 'end'
}

references = {
    'k' : 'D.C.',
    'K' : 'D.S.',
    'i' : 'al Coda',
    'I' : 'al Fine'
}

accidentals = {
    '-' : 'bemol',
    '=' : 'sostenido',
    '--' : 'doble bemol',
    '==' : 'doble sostenido',
    '-=' : 'becuadro',
    '=-' : 'becuadro'
}

articulations = {
    '\'' : 'staccato',
    '\"' : 'tenuto',
    '\'\'' : 'staccatissimo',
    '\"\"' : 'fermatta'
}

accidentals_short = {
    '-' : '(b)',
    '=' : '(s)',
    '--' : '(bb)',
    '==' : '(ss)',
    '-=' : '(n)',
    '=-' : '(n)'
}

dynamics = {
    '\\|' : 'mp',
    '|\\' : 'mf',
    '\\' : 'p',
    '|' : 'f',
    '\\\\' : 'pp',
    '||' : 'ff',
    '\\\\\\' : 'ppp',
    '|||' : 'fff',
    '\\\\|' : 'sfz',
    '||\\' : 'sfz',
    '\\\\`' : 'fp',
    '\\\\\\|' : 'fp',
    '||`' : 'fp',
    '|||\\' : 'fp'
}

gradual_dynamics = {
    'l' : 'crescendo',
    'll' : 'crescendo',
    'L' : 'decrescendo'
}

ornaments = {
    '[' : 'mordente',
    '{' : 'grupeto',
    '[`' : 'mordente inv.',
    '{`' : 'grupeto inv.',
    '[[' : 'trino[1/8]',
    '[[[' : 'trino[1/8]', # a propósito
    '[[[[' : 'trino[2/8]',
    '[[[[[' : 'trino[3/8]',
    '[[[[[[' : 'trino[4/8]'
}

circle_of_fifths = {
    '-7' : 'Cb / Abm', # equivalente a 5
    '-6' : 'Gb / Ebm', # equivalente a 6
    '-5' : 'Db / Bbm', # equivalente a 7
    '-4' : 'Ab / Fm',
    '-3' : 'Eb / Cm',
    '-2' : 'Bb / Gm',
    '-1' : 'F / Dm',
    '0' : 'C / Am',
    '1' : 'G / Em',
    '2' : 'D / Bm',
    '3' : 'A / Fsm',
    '4' : 'E / Csm',
    '5' : 'B / Gsm', #  equivalente a -7
    '6' : 'Fs / Dsm', # equivalente a -6
    '7' : 'Cs / Asm' # equivalente a -5
}


#--- SYMBOLS ---#

digits = '0123456789'

note_range = ''.join([
    'zxcvbnm',
    'asdfghj',
    'qwertyu',
    '1234567',
    '890'
])

note_range_size = len(note_range)

note_range += note_range[:21].upper()
note_range += '!@#$%^&*()'

chord_set = note_range

operators = {
    'prolonger': '~',
    'inverter': '`'
}

punctuation = {
    'splitters': [
        ' ',
        '/',
        '//'
    ],
    'special_splitter': '/',
    
    'barline': ',',
    'double_barline': ',,',
    'bold_double_barline': '.',
    'repeat_from': ';',
    'repeat_to': ':',
    
    'timesig': '~'
}

key_symbols = [
    '_', # G
    '+' # F
]

rests = [
    ']',
    '}'
]

accidentals_symbols = [
    '-', # bemol
    '=' # sostenido
]

articulations_symbols = [
    '\'', # stacatto
    '\"' # tenuto
]

note_dot = '<'
accent_mark = '>'

all_diacritics = accidentals_symbols + articulations_symbols
all_diacritics.extend([note_dot, accent_mark])

ornaments_symbols = [
    '[', # mordente
    '{' # grupeto
]

dynamics_symbols = [
    '\\', # piano
    '|' # forte
]

gradual_dynamics_symbols = [
    'l', # crescendo
    'L' # decrescendo
]

arpegio = 'P' # chord ornament

navigation = {
    'coda' : 'i',
    'segno' : 'I'
}

repeat_reference = [
    'k',
    'K'
]

pedal = {
    'down' : 'p',
    'up' : 'pp'
}


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


#--- SYNTAX ---#

def get_pitch(symbol):
    for i in range(len(note_range)):
        if note_range[i] == symbol:
            return i
    
    raise InvalidSymbolError

def get_splitter_length(symbol):
    return splitter_length[symbol]

def tokenize(expr):
    if len(expr) <= 1:
        return [expr]

    stack = [expr[0]]

    for current in expr[1:]:
        previous = stack.pop()
        # -- group all contextually linked symbols
        if ( # new line
            current == 'n' and previous == '\\'
        ) or ( # quarter space
            current == punctuation['special_splitter'] and
            previous == punctuation['special_splitter']
        ) or ( # double barline
            current == punctuation['barline'] and
            previous == punctuation['barline']
        ) or ( # C-clef
            (current == key_symbols[0] and previous == key_symbols[1]) or
            (current == key_symbols[1] and previous == key_symbols[0])
        ) or ( # key signature
            previous[0] in clefs and
            current in accidentals_symbols and
            (not re.search('-|=',previous) or len(re.findall('-|=', previous)) < 7) and
            (
                previous[-1] in clefs or
                (current == accidentals_symbols[0] and previous[-1] == accidentals_symbols[0]) or
                (current == accidentals_symbols[1] and previous[-1] == accidentals_symbols[1])
            )
        ) or ( # time signature
            (
                (
                    len(previous) <= 2 and
                    previous[0] == punctuation['timesig'] and
                    current in digits
                ) or ( # case 12 is numumerator or 16 is denominator
                    len(previous) == 3 and
                    re.search('^(12)|(16)$', previous[1:] + current)
                ) or (
                    previous == '~121' and current == '6'
                )
            ) and (
                stack[-1] in clefs or
                stack[-1] in [
                    punctuation['barline'],
                    punctuation['barline'],
                    punctuation['double_barline'],
                    punctuation['bold_double_barline']
                ]
            )
        ) or ( # chords
            current in chord_set and previous[0] in chord_set
        ) or ( # altered notes
            (   (current in all_diacritics) or
                (current == operators['prolonger'] and not re.search('~[-=\'\"<>]*~', previous)) or # no more than 2 '~' for each note
                (current == operators['inverter'] and re.search('[^\[](\[|\{)$', previous)) or # inverted ornaments
                (current == '[' and (re.search('[^\[]\[{1,5}$', previous) or not re.search('\[',previous)) and not re.search('\{',previous)) or # mordent, trills, no double ornamentation
                (current == '{' and not re.search('\[|\{',previous)) # grupetto, no double ornamentation
            ) and (
                previous[0] in note_range
            )
        ) or ( # dynamics
            (current in dynamics_symbols or current == operators['inverter']) and (previous[0] in dynamics_symbols) and ((previous + current) in dynamics)
        ) or ( # gradual dynamics: crescendo, long form
            current == 'l' and previous == 'l'
        ) or ( # repeats
            (current == 'o' or current == operators['inverter']) and previous == 'o'
        ) or ( # repeat references with indications
            current in ['i','I'] and previous in repeat_reference
        ) or ( # octavation
            (current == 'O' or current == operators['inverter']) and previous == 'O'
        ) or ( # pedal mark 'up'
            current == 'p' and previous == 'p'
        ) or ( # rest prolongation
            current == operators['prolonger'] and re.search('(\]~{0,2}$)|(\}~{0,1}$)', previous)
        ) or ( # error sign
            current == punctuation['bold_double_barline'] and previous == punctuation['bold_double_barline']
        ):
            stack.append(previous + current)
        else:
            stack.append(previous)
            stack.append(current)
        
    return stack

def parse(expr):
    stack = tokenize(expr)
    tree = []
    current_key_signature = KeySignature(clefs['_']) #   this variable is the last defined key signature and affects all
    #                                                       succeeding note objects. If no key signature is yet defined when
    #                                                       a note is entered, the G-clef without accidentals is assumed.

    for token in stack:
        if token == '\n':
            tree.append(Newline())

        elif token in punctuation['splitters']:
            tree.append(Splitter( get_splitter_length(token) ))
            continue

        elif token[0] in key_symbols:
            split_token = re.search(r'^([\+_]{1,2})([-|=]*)', token)
            if (split_token and split_token.group(1) in clefs):
                sign =  0 if not split_token.group(2) else ( \
                        -1 if split_token.group(2)[0] == '-' else \
                        1)#   split_token.group(2)[0] == '='
                new_key_signature = sign * len(split_token.group(2))
                tree.append( KeySignature(clefs[split_token.group(1)], new_key_signature) )
                current_key_signature = KeySignature(clefs[split_token.group(1)], new_key_signature)
                continue

        elif token[0] == punctuation['timesig']:
            if len(token) == 3:
                tree.append( TimeSignature(token[1], token[2]) )
            elif (len(token) == 4 or len(token) == 5):
                if re.search('^12', token[1:]):
                    token_numerator = 12
                else:
                    token_numerator = token[1]
                if re.search('16$',token):
                    token_denominator = 16
                else:
                    token_denominator = token[-1]
                tree.append( TimeSignature(token_numerator, token_denominator) )
            else:
                tree.append( ErrorSign() )
            continue

        elif token == punctuation['barline']:
            tree.append( MeasureEnd() )
            continue

        elif token == punctuation['double_barline']:
            tree.append( SectionEnd() )
            continue

        elif token == punctuation['bold_double_barline']:
            tree.append( End() )
            continue

        elif token == punctuation['repeat_from']:
            tree.append( RepeatFrom() )
            continue

        elif token == punctuation['repeat_to']:
            tree.append( RepeatTo() )
            continue

        elif token in repetition:
            if type(repetition[token]) is int:
                tree.append( RepeatSectionStart(repetition[token]) )
            else:
                tree.append( RepeatSectionEnd() )
            continue

        elif token in octavation:
            if type(octavation[token]) is int:
                tree.append ( OctavationStart() )
            else:
                tree.append( OctavationEnd() )
            continue

        elif token[0] in dynamics_symbols:
            tree.append ( Dynamic(dynamics[token]) )
            continue

        elif token[0] in gradual_dynamics_symbols:
            tree.append ( GradualDynamic(gradual_dynamics[token]) )
            continue

        elif token == navigation['coda']:
            tree.append( Coda() )
            continue

        elif token == navigation['segno']:
            tree.append( Segno() )
            continue

        elif token[0] in repeat_reference:
            if len(token) > 0:
                tree.append( FromTo(references[token[0]], references[token[1]]) )
            else:
                tree.append( FromTo(references[token]) )
            continue

        elif token == pedal['down']:
            tree.append( PedalDown() )
            continue

        elif token == pedal['up']:
            tree.append( PedalUp() )
            continue

        elif token == arpegio and isinstance(tree[-1], Chord):
            tree[-1].add_arpeggio()
            continue

        elif token == '..' and not isinstance(tree[-1], Chord): # internally used to create beams between eighth notes
            tree.append ( ErrorSign() )
            continue
        
        elif token[0] in rests:
            for symbol in token:
                if symbol == ']':
                    tree.append ( Rest(0) )
                elif symbol == '}':
                    tree.append ( Rest(1) )
                else:
                    tree[-1].increase_length_exponent()
            continue

        chord_notes = []

        for symbol in token:
            try:
                note_pitch = get_pitch(symbol)
                chord_notes.append( Note(note_pitch, current_key_signature) )
            except InvalidSymbolError:
                if symbol == operators['prolonger']:
                    chord_notes[-1].increase_length_exponent()
                if symbol == note_dot and len(chord_notes) > 0:
                    chord_notes[-1].add_dot_length()
                if ((symbol in accidentals_symbols or
                    symbol in articulations_symbols or
                    symbol in ornaments_symbols or
                    symbol == operators['inverter'] or # for the case of inverted ornamentation
                    symbol == accent_mark
                    ) and len(chord_notes) > 0):
                    chord_notes[-1].add_diacritical_mark(symbol)
        
        if len(chord_notes) > 0:
            tree.append( Chord(chord_notes) )

    return tree
