class InvalidSymbolError extends Error

class Note
    constructor: (@octave) ->
        @set_octave(@octave)

    set_octave: (octave) ->
        @octave = octave
        @name = scale[@octave % 7]
        @scale_index = parseInt(@octave / 7)

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

class Newline
    constructor: ->

    get_str: ->
        return 'newline'

class Key
    constructor: (@key) ->

    get_str: ->
        return "(key #{@key})"
