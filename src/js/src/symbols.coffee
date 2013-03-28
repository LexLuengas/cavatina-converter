digits = '0123456789'

operators = {
    'splitters': [
        ' '
        '/'
        '//'
        '?'
    ]
    'special_splitter': '/'
    'timesig': '~'
    'note_length_modifier': '~'
    'measure': ','
}

octaves = [
    'zxcvbnm'
    'asdfghj'
    'qwertyu'
    '1234567'
    '890'
].join ''

octaves_size = octaves.length

octaves += (octaves.substr 0, 21).toUpperCase()
octaves += '!@#$%^&*()'

keys = [
    '_'
    '+'
]

chord_set = octaves
