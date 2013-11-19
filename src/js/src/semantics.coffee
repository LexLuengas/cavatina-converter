scale = [
    'C' #'do'
    'D' #'re'
    'E' #'mi'
    'F' #'fa'
    'G' #'sol'
    'A' #'la'
    'B' #'si'
]

splitter_length = { # in quarters
    ' ':    4
    '/':    2
    '//':   1
}

clefs = {
    '_':    'G' #'sol'
    '+':    'F' #'fa'
    '_+':   'C' #'do'
    '+_':   'C' #'do'
}

accidentals = {# arreglar key signature, que piensa que esto es un array y no un diccionario
    '-' : 'bemol'
    '=' : 'sostenido'
    '--' : 'doble bemol'
    '==' : 'doble sostenido'
    '-=' : 'becuadro'
    '=-' : 'becuadro'
}

articulations = {
    '\'' : 'staccato'
    '\"' : 'tenuto'
    '\'\'' : 'staccatissimo'
    '\"\"' : 'fermatta'
}

accidentals_short = {# arreglar key signature, que piensa que esto es un array y no un diccionario
    '-' : '(b)'
    '=' : '(s)'
    '--' : '(bb)'
    '==' : '(ss)'
    '-=' : '(n)'
    '=-' : '(n)'
}

circle_of_fifths = {
    '-7' : 'Cb / Abm' # equivalente a 5
    '-6' : 'Gb / Ebm' # equivalente a 6
    '-5' : 'Db / Bbm' # equivalente a 7
    '-4' : 'Ab / Fm'
    '-3' : 'Eb / Cm'
    '-2' : 'Bb / Gm'
    '-1' : 'F / Dm'
    '0' : 'C / Am'
    '1' : 'G / Em'
    '2' : 'D / Bm'
    '3' : 'A / Fsm'
    '4' : 'E / Csm'
    '5' : 'B / Gsm' #  equivalente a -7
    '6' : 'Fs / Dsm' # equivalente a -6
    '7' : 'Cs / Asm' # equivalente a -5
}
