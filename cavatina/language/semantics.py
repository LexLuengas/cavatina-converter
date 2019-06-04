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
    '+' : 'G', #'sol'
    '_' : 'F', #'fa'
    '_+' : 'C', #'do'
    '+_' : 'C' #'do'
}

common_time = {
    'c' : 'c',
    'c~' : 'cut'
}

repetition = {
    'o' : '1',
    'oo' : '2',
    'ooo' : '3',
    'oooo' : '1,2',
    'o`' : 'end'
}

octavation = {
    'O' : 1,
    'OO' : 0,
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
    '\"\"' : 'fermata'
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
    '\\\\|' : 'sf',
    '||\\' : 'sf',
    '\\\\`' : 'fp',
    '\\\\\\|' : 'fp',
    '||`' : 'fp',
    '|||\\' : 'fp'
}

gradual_dynamics = {
    'l' : 'crescendo',
    'll' : 'crescendo',
    'l`' : 'decrescendo'
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
