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
    '_'
    '+'
]

accidentals_symbols = [
    '-'
    '='
]

articulations_symbols = [
    '\''
    '\"'
]

note_dot = '<'

all_diacritics = (accidentals_symbols.concat articulations_symbols)
all_diacritics.push note_dot
