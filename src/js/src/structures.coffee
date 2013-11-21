class InvalidSymbolError extends Error

MatchIndex = (regexpr,array) ->
    for i in [0...array.length] # returns index of the first entry which matches regexpr, or -1 if it wasn't matched
        if regexpr.test(array[i])
            return i
    return -1

class TimeInterval
    constructor: (@length_exponent) ->
        @length_base = 1 # by 1/8
        @denominator = 8
        @set_length_exponent(@length_exponent or 0)

    set_length_exponent: (length_exponent) ->
        @length_exponent = length_exponent
        @length = @length_base * (Math.pow 2, @length_exponent)

    increase_length_exponent: ->
        @set_length_exponent(@length_exponent + 1)

    add_dot_length: ->
        if @length_base * (Math.pow 2, @length_exponent) > 1
            @length = 3 * @length_base * (Math.pow 2, @length_exponent-1)
        else
            @denominator = 2 * @denominator
            @length = 3 * @length_base * (Math.pow 2, @length_exponent)

class Note extends TimeInterval
    constructor: (@pitch, @key_signature, @length_exponent) ->
        super(@length_exponent)
        @set_pitch(@pitch)
        @note_diacritics = [] # list of strings containing all note alterations and note articulations as *input* symbols.
        signature_notes = @key_signature.get_signature_notes()
        if @name in signature_notes
            @keyAccidental = true # remember if added accidental comes from key signature
            if signature_notes.charAt(0) == 'F'
                @add_diacritical_mark('=') # sostenido
            if signature_notes.charAt(0) == 'B'
                @add_diacritical_mark('-') # bemol

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
        if (mark in accidentals_symbols and MatchIndex(/-|=/, @note_diacritics) != -1) #  double accidentals
            mark_index = @note_diacritics.indexOf(mark)
            if mark_index != -1
                if not @keyAccidental # key signature consistency
                    @note_diacritics[mark_index] = switch
                        when mark == '-' then '--'
                        when mark == '=' then '=='
            else switch mark
                when '-'
                    if not @keyAccidental
                        @note_diacritics[@note_diacritics.indexOf('=')] = '=-'
                    else
                        @note_diacritics[@note_diacritics.indexOf('=')] = '-'
                when '='
                    if not @keyAccidental
                        @note_diacritics[@note_diacritics.indexOf('-')] = '-='
                    else
                        @note_diacritics[@note_diacritics.indexOf('-')] = '='
            @keyAccidental = false
        else if (mark in accidentals_symbols and (MatchIndex(/[-|=][-|=]/, @note_diacritics)) == -1) # base case, do not exceed 2 diacritic maximum
            @note_diacritics.push mark
        
        # articulations
        else if (mark in articulations_symbols and MatchIndex(/\'|\"/, @note_diacritics) != -1) #  double articulations
            mark_index = @note_diacritics.indexOf(mark)
            if mark_index != -1
                @note_diacritics[mark_index] = switch
                    when mark == '\'' then '\'\''
                    when mark == '\"' then '\"\"'
        else if (mark in articulations_symbols and (MatchIndex(/[\'\']|[\"\"]/, @note_diacritics)) == -1) # base case, do not exceed 2 diacritic maximum
            @note_diacritics.push mark
        
        # accent
        else if mark == accent_mark
            @note_diacritics.push mark
        
        # ornamentation
        else if (mark == operators.inverter and MatchIndex(/\[|\{/, @note_diacritics) != -1) # inversion
            lastOrnmIndex = @note_diacritics.length - 1 # last index of simple ornament
            while @note_diacritics[lastOrnmIndex] not in ornaments_symbols
                lastOrnmIndex = lastOrnmIndex - 1
            @note_diacritics[lastOrnmIndex] = @note_diacritics[lastOrnmIndex] + '`'
        else if (mark == '[' and MatchIndex(/\[+/, @note_diacritics) != -1) # trills
            mark_index = MatchIndex(/\[+/, @note_diacritics)
            @note_diacritics[mark_index] = @note_diacritics[mark_index] + '['
        else if mark in ornaments_symbols # base case
            @note_diacritics.push mark

    get_name: ->
        note_accidentals = (accidentals_short[d] for d in @note_diacritics when accidentals_short[d] != undefined)
        note_articulations = (articulations[d] for d in @note_diacritics when articulations[d] != undefined)
        note_ornaments = (ornaments[d] for d in @note_diacritics when ornaments[d] != undefined)
        if accent_mark in @note_diacritics
            note_articulations.push 'accent'
        return "#{@name}#{note_accidentals} #{@octave} [#{@length}/#{@denominator}]" + 
            (if note_articulations.length > 0 then (", " + note_articulations.join(", ")) else "") + 
            (if note_ornaments.length > 0 then (", " + note_ornaments.join(", ")) else "")

class Chord
    constructor: (@notes) -> # a list of Note objects
        @arpeggio = false

    add_arpeggio: ->
        @arpeggio = true

    get_str: ->
        notes = (note.get_name() for note in @notes).join('; ')
        if @arpeggio
            return "chord [arpeggio](#{notes})"
        else
            return "chord (#{notes})"

class Rest extends TimeInterval
    get_str: ->
        return "(rest [#{@length}/#{@denominator}])"
        

class Splitter
    constructor: (@length) ->

    get_str: ->
        return "space (#{@length}/4)"

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
        return "||:"

class RepeatTo
    get_str: ->
        return ":||"

class RepeatSectionStart
    constructor: (@n) ->

    get_str: ->
        return "(#{@n}th repeat section start)"

class RepeatSectionEnd
    constructor: ->

    get_str: ->
        return "(repeat section end)"
        
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

class Dynamic
    constructor: (@dynamic) ->

    get_str: ->
        return "(dynamic: #{@dynamic})"

class GradualDynamic
    constructor: (@gdynamic) ->

    get_str: ->
        return "(change dynamic: #{@gdynamic})"

class OctavationStart
    constructor: () ->

    get_str: ->
        return "(8va)---{"

class OctavationEnd
    constructor: () ->

    get_str: ->
        return "}(8va)"

class Segno
    constructor: () ->

    get_str: ->
        return "(segno)"

class Coda
    constructor: () ->

    get_str: ->
        return "(coda)"

class FromTo
    constructor: (@from,@to) ->

    get_str: ->
        return "(#{@from}" + (if @to != undefined then " #{@to})" else ")")

class PedalDown
    constructor: () ->

    get_str: ->
        return '(pedal down)'

class PedalUp
    constructor: () ->

    get_str: ->
        return '(pedal up)'

class Newline
    constructor: ->

    get_str: ->
        return '(newline)'

class ErrorSign
    get_str: ->
        return '(error symbol)'
