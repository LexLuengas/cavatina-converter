class InvalidSymbolError extends Error

class Note
    constructor: (@octave) ->
        @set_octave(@octave)

    set_octave: (octave) ->
        @octave = octave
        for i in [0..scale.length]
            if @octave % 7 == i + 1
                @name = scale[i]
                @scale_index = parseInt(@octave / scale.length)

    get_name: ->
        return "#{@name} #{@scale_index}"


class Chord
    constructor: (@notes) ->

    get_str: ->
        notes = (note.get_name() for note in @notes).join(' ')
        return "chord (#{notes})"


class Splitter
    constructor: (@length) ->

    get_str: ->
        return "space (#{@length}/4)"
