class InvalidSymbolError extends Error

presenceTest = (regexpr,array) ->
    for i in array # returns true if any of the entries matches regexpr
        if regexpr.test(i)
            return true
    return false

class Note
    constructor: (@pitch, @key_signature, @length_exponent) ->
        @length_base = 1 # by 1/8
        @set_pitch(@pitch)
        @set_length_exponent(@length_exponent or 0)
        @note_diacritics = [] # list of strings containing all note alterations and note articulations as *input* symbols.
        signature_notes = @key_signature.get_signature_notes()
        if signature_notes.indexOf(@name) != -1
            if signature_notes.charAt(0) == 'F'
                @add_diacritical_mark('=') # sostenido
            if signature_notes.charAt(0) == 'B'
                @add_diacritical_mark('-') # bemol

    set_length_exponent: (length_exponent) ->
        @length_exponent = length_exponent
        @length = @length_base * (Math.pow 2, @length_exponent)

    increase_length_exponent: ->
        @set_length_exponent(@length_exponent + 1)

    set_pitch: (pitch) ->
        if pitch >= range_size
            @length_base = 2
        @pitch = pitch % range_size
        @name = switch
            when @key_signature.get_clef() == 'G' then scale[@pitch % 7]
            when @key_signature.get_clef() == 'F' then scale[(@pitch + 2) % 7]
            when @key_signature.get_clef() == 'C' then scale[(@pitch + 1) % 7]
        @octave = switch
            when @key_signature.get_clef() == 'G' then parseInt(@pitch / 7) + 3
            when @key_signature.get_clef() == 'F' then parseInt((@pitch + 2) / 7) + 1
            when @key_signature.get_clef() == 'C' then parseInt((@pitch + 1) / 7) + 2
        
    add_diacritical_mark: (mark) ->
        # accidentals
        if (mark in accidentals_symbols and presenceTest(/-|=/,@note_diacritics)) #  double accidentals
            mark_index = @note_diacritics.indexOf(mark)
            if mark_index != -1
                @note_diacritics[mark_index] = switch
                    when mark == '-' then '--'
                    when mark == '=' then '=='
            else switch mark
                when '-'
                    @note_diacritics[@note_diacritics.indexOf('=')] = '=-'
                when '='
                    @note_diacritics[@note_diacritics.indexOf('-')] = '-='
        else if (mark in accidentals_symbols and !(presenceTest(/[-|=][-|=]/, @note_diacritics)) ) # do not exceed 2 diacritic maximum
            @note_diacritics.push mark
        
        # articulations
        if (mark in articulations_symbols and presenceTest(/\'|\"/,@note_diacritics)) #  double articulations
            mark_index = @note_diacritics.indexOf(mark)
            if mark_index != -1
                @note_diacritics[mark_index] = switch
                    when mark == '\'' then '\'\''
                    when mark == '\"' then '\"\"'
        else if (mark in articulations_symbols and !(presenceTest(/[\'\']|[\"\"]/, @note_diacritics)) ) # do not exceed 2 diacritic maximum
            @note_diacritics.push mark

    get_name: ->
        note_accidentals = (accidentals_short[n] for n in @note_diacritics when accidentals_short[n] != undefined)
        note_articulations = (articulations[n] for n in @note_diacritics when articulations[n] != undefined)
        
        return "#{@name}#{note_accidentals} #{@octave} [#{@length}/8]" + (if note_articulations.length > 0 then ('; ' + note_articulations) else '')

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
    constructor: (@clef, @signature) -> # signature: an integer in the interval [-7,7]
        @sharps_or_flats = switch
            when @signature > 0 then 'sharps'
            when @signature < 0 then 'flats'
            else 'sharps/flats'
        @amount = Math.abs(@signature or 0)
        @signature_notes = switch
            when @signature > 0 then 'FCGDAEB'.substring(0,Math.abs(signature))
            when @signature <= 0 then 'BEADGCF'.substring(0,Math.abs(signature))
            else ''
    
    get_clef: ->
        return @clef
    
    get_signature_notes: ->
        return @signature_notes

    get_str: ->
        return "(clef #{@clef}, #{@amount} #{@sharps_or_flats})"

class TimeSignature
    constructor: (@numerator, @denominator) ->

    get_str: ->
        return "(timesig #{@numerator} / #{@denominator})"


class ErrorSign
    get_str: ->
        return '(error symbol)'
