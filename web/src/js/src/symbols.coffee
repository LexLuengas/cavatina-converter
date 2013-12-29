digits = '0123456789'

range = [
    'zxcvbnm'
    'asdfghj'
    'qwertyu'
    '1234567'
    '890'
].join ''

range_size = range.length

range += (range.substr 0, 21).toUpperCase()
range += '!@#$%^&*()'

chord_set = range

operators = {
    'prolonger': '~'
    'inverter': '`'
}

punctuation = {
    'splitters': [
        ' '
        '/'
        '//'
    ]
    'special_splitter': '/'
    
    'barline': ','
    'double_barline': ',,'
    'bold_double_barline': '.'
    'repeat_from': ';'
    'repeat_to':':'
    
    'timesig': '~'
}

key_symbols = [
    '_' # G
    '+' # F
]

rests = [
    ']'
    '}'
]

accidentals_symbols = [
    '-' # bemol
    '=' # sostenido
]

articulations_symbols = [
    '\'' # stacatto
    '\"' # tenuto
]

note_dot = '<'
accent_mark = '>'

ornaments_symbols = [
    '[' # mordente
    '{' # grupeto
]

dynamics_symbols = [
    '\\' # piano
    '|' # forte
]

gradual_dynamics_symbols = [
    'l' # crescendo
    'L' # decrescendo
]

arpegio = 'P' # chord ornament

all_diacritics = (accidentals_symbols.concat articulations_symbols)
all_diacritics.push(note_dot, accent_mark)

navigation = {
    'coda' : 'i'
    'segno' : 'I'
}

repeat_reference = [
    'k'
    'K'
]

pedal = {
    'down' : 'p'
    'up' : 'pp'
}