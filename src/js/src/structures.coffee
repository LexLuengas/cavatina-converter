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
