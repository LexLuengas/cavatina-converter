class InvalidSymbolError extends Error

class Note
    constructor: (@pitch, @length_exponent) ->
        @length_base = 1 # by 1/8
        @set_pitch(@pitch)
        @set_length_exponent(@length_exponent or 0)
        @note_diacritics = [] # list of strings containing all note alterations and note articulations.

    set_length_exponent: (length_exponent) ->
        @length_exponent = length_exponent
        @length = @length_base * (Math.pow 2, @length_exponent)

    increase_length_exponent: ->
        @set_length_exponent(@length_exponent + 1)

    set_pitch: (pitch) ->
        if pitch >= range_size
            @length_base = 2
        @pitch = pitch % range_size
        @name = scale[@pitch % 7]
        @octave = parseInt(@pitch / 7) + 3
        
    add_diacritical_mark: (mark) ->
        if (accidentals[mark] != undefined or articulations[mark] != undefined or mark == note_dot) # pongo esto en el 'parse'?
            @note_diacritics.push mark

    get_name: ->
        return "#{@name} #{@octave} [#{@length}/8]" # 'octave' is the actual octave used in musical notation

class Chord
    constructor: (@notes) -> # a list of Note objects

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

class MeasureEnd
    get_str: ->
        return "(measure end)"
        
class SectionEnd
    get_str: ->
        return "(section end)"

class End
    get_str: ->
        return "(end)"
        
class RepeatFrom
    get_str: ->
        return "(repeat from)"
        
class RepeatTo
    get_str: ->
        return "(repeat to)"
        
class KeySignature
    constructor: (@cleff, @signature) -> # signature: an integer in the interval [-7,7]
        @sharps_or_flats = switch
            when @signature > 0 then 'sharps'
            when @signature < 0 then 'flats'
            else ''
        @amount = Math.abs(@signature)

    get_str: ->
        if @amount != 0
            return "(cleff #{@cleff}, #{@amount} #{@sharps_or_flats})"
        else
            return "(cleff #{@cleff}, 0 sharps/flats)"

class TimeSignature
    constructor: (@numerator, @denominator) ->

    get_str: ->
        return "(timesig #{@numerator} / #{@denominator})"


class ErrorSign
    get_str: ->
        return '(error symbol)'
