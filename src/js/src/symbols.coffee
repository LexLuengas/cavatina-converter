digits = '0123456789'

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

key_symbols = [
    '_'
    '+'
]

chord_set = range
