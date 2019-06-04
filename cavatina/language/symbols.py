
digits = '0123456789'

note_range = ''.join([
    'zxcvbnm',
    'asdfghj',
    'qwertyu',
    '1234567',
    '890'
])

eighth_note_range = len(note_range)

note_range += note_range[:21].upper()
note_range += '!@#$%^&*()'

chord_set = note_range

operators = {
    'prolonger': '~',
    'inverter': '`'
}

punctuation = {
    'splitters': [ # TODO: Amend information loss (splitter length/size)
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

    'long': {
        'systemic_barline' : ',\\',
        'grand_staff' : ',\\\\',
        'double_systemic_barline' : [',,\\', ',\\,'],
        'bold_systemic_barline' : '.\\',
        'long_repeat_from' : ';\\',
        'long_repeat_to' : ':\\'
    }
}

simple_punctuation = [
    ',',
    '.',
    ',,',
    ';',
    ':'
]

time_signature = '~'

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
tie = 'L'
triplet = '?'

all_diacritics = accidentals_symbols + articulations_symbols
all_diacritics.extend([note_dot, accent_mark, tie])

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
