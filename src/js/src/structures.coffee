class InvalidOctaveSymbolError extends Error

class Note
    constructor: (@octave) ->

    get_name: ->
        for i in [0..scale.length]
            if @octave % (i + 1) == 0
                name = scale[i]
                scale_index = @octave / scale.length
                return "#{name} #{scale_index}"


class Chord
    constructor: (@notes) ->

    get_str: ->
        notes = [note.get_name() for note in @notes].toString()
        return "chord (#{notes})"
