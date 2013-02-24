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

octaves += octaves.toUpperCase()

keys = [
    '_'
    '+'
]

chord_set = octaves


scale = [
    'do'
    're'
    'mi'
    'fa'
    'sol'
    'la'
    'si'
]


splitter_length = { # in quarters
    ' ':    4
    '/':    2
    '//':   1
    '?':    3
}

key_tokens = {
    '_':    'sol'
    '+':    'fa'
    '_+':   'do'
    '+_':   'do'
}


class InvalidSymbolError extends Error

class Note
    constructor: (@octave, @length_exponent) ->
        @length_base = 1 # by 1/8
        @set_octave(@octave)
        @set_length_exponent(@length_exponent or 0)

    set_length_exponent: (length_exponent) ->
        @length_exponent = length_exponent
        @length = @length_base * (Math.pow 2, @length_exponent)

    increase_length_exponent: ->
        @set_length_exponent(@length_exponent + 1)

    set_octave: (octave) ->
        if octave >= octaves_size
            @length_base = 2
        @octave = octave % octaves_size
        @name = scale[@octave % 7]
        @scale_index = parseInt(@octave / 7)

    get_name: ->
        return "#{@name} #{@scale_index} [#{@length}/8]"


class Chord
    constructor: (@notes) ->

    get_str: ->
        notes = (note.get_name() for note in @notes).join(' ')
        return "chord (#{notes})"


class Splitter
    constructor: (@length) ->

    get_str: ->
        return "space (#{@length}/4)"

class Newline
    constructor: ->

    get_str: ->
        return '(newline)'

class Key
    constructor: (@key) ->

    get_str: ->
        return "(key #{@key})"

class MeasureEnd
    get_str: ->
        return "(measure end)"

class TimeSignature
    constructor: (@numerator, @denominator) ->

    get_str: ->
        return "(timesig #{@numerator} / #{@denominator})"


class ErrorSign
    get_str: ->
        return '(error symbol)'


get_octave = (symbol) ->
    for i in [0...octaves.length]
        if (octaves.charAt i) == symbol
            return i

    throw new InvalidSymbolError

get_splitter_length = (symbol) ->
    return splitter_length[symbol]

tokenize = (expr) ->
    if expr.length <= 1
        return [expr]

    stack = [expr.charAt(0)]

    for current in (expr.charAt(i) for i in [1...expr.length])
        previous = stack.pop()
        if (
            current == operators.special_splitter and
            previous == operators.special_splitter
        ) or (
            current == 'n' and previous == '\\'
        ) or (
            (current == keys[0] and previous == keys[1]) or
            (current == keys[1] and previous == keys[0])
        ) or (
            current in chord_set and previous.charAt(0) in chord_set
        ) or (
            current == operators.note_length_modifier and
            previous.charAt(Math.max 0, previous.length - 2) in octaves
        ) or (
            previous.length < 3 and
            previous.charAt(0) == operators.timesig and
            current in digits and
            key_tokens[stack[stack.length - 1]] != undefined
        )
            stack.push (previous + current)
        else
            stack.push previous
            stack.push current

    return stack

parse = (expr) ->
    stack = tokenize expr

    tree = []

    for token in stack
        if token == '\n'
            tree.push (new Newline())

        else if token in operators.splitters
            tree.push (new Splitter (get_splitter_length token))
            continue

        else if key_tokens[token] != undefined
            tree.push (new Key key_tokens[token])
            continue

        else if token == operators.measure
            tree.push (new MeasureEnd)
            continue

        else if token.charAt(0) == operators.timesig
            if token.length == 3
                tree.push (new TimeSignature token.charAt(1), token.charAt(2))
            else
                tree.push (new ErrorSign)
            continue

        chord_notes = []

        for symbol in token
            try
                chord_notes.push (new Note (get_octave symbol))
            catch error
                if symbol == operators.note_length_modifier
                    chord_notes[chord_notes.length - 1]
                        .increase_length_exponent()

        if chord_notes.length > 0
            tree.push (new Chord chord_notes)

    return tree


(($) ->
    log_result = (string) ->
    	$('#result').html string

    update = ->
    	tree = parse ($ 'textarea').val()
    	log_result ((n.get_str() for n in tree).join "\n")

    init = () ->
        $('textarea')
        	.keyup ->
        	    update()
        	.keydown ->
        	    update()
        	.keypress ->
        	    update()

    $ ->
        init()
)(jQuery)
