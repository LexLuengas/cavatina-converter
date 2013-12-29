

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
