get_pitch = (symbol) ->
    for i in [0...range.length]
        if (range.charAt i) == symbol
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
        # -- group all contextually linked symbols
        if ( # new line
            current == 'n' and previous == '\\'
        ) or ( # quarter space
            current == punctuation.special_splitter and
            previous == punctuation.special_splitter
        ) or ( # double barline
            current == punctuation.barline and
            previous == punctuation.barline
        ) or ( # C-clef
            (current == key_symbols[0] and previous == key_symbols[1]) or
            (current == key_symbols[1] and previous == key_symbols[0])
        ) or ( # key signature
            clefs[previous.charAt(0)] != undefined and
            current in accidentals_symbols and
            (not /-|=/g.test(previous) or previous.match(/-|=/g).length < 7) and
            (
                clefs[previous.charAt(previous.length - 1)] != undefined or
                (current == accidentals_symbols[0] and previous.charAt(previous.length - 1) == accidentals_symbols[0]) or
                (current == accidentals_symbols[1] and previous.charAt(previous.length - 1) == accidentals_symbols[1])
            )
        ) or ( # time signature
            (
                (
                    previous.length <= 2 and
                    previous.charAt(0) == punctuation.timesig and
                    current in digits
                ) or ( # case 12 is numumerator or 16 is denominator
                    previous.length == 3 and
                    /^(12)|(16)$/.test(previous.substring(1,previous.length) + current)
                ) or (
                    previous == '~121' and current == '6'
                )
            ) and (
                clefs[stack[stack.length - 1]] != undefined or
                stack[stack.length - 1] in [
                    punctuation.barline,
                    punctuation.barline,
                    punctuation.double_barline,
                    punctuation.bold_double_barline
                ]
            )
        ) or ( # chords
            current in chord_set and previous.charAt(0) in chord_set
        ) or ( # altered notes
            (   (current in all_diacritics) or
                (current == operators.prolonger and not /~[-=\'\"<>]*~/g.test(previous) ) or # no more than 2 '~' for each note
                (current == operators.inverter and /[^\[](\[|\{)$/.test(previous)) or # inverted ornaments
                (current == '[' and (/[^\[]\[{1,5}$/g.test(previous) or not /\[/.test(previous)) and not /\{/.test(previous)) or # mordent, trills, no double ornamentation
                (current == '{' and not /\[|\{/.test(previous)) # grupetto, no double ornamentation
            ) and (
                previous.charAt(0) in range
            )
        ) or ( # dynamics
            (current in dynamics_symbols or current == operators.inverter) and (previous.charAt(0) in dynamics_symbols) and (dynamics[previous + current] != undefined)
        ) or ( # gradual dynamics: crescendo, long form
            current == 'l' and previous == 'l'
        ) or ( # repeats
            (current == 'o' or current == operators.inverter) and previous == 'o'
        ) or ( # repeat references with indications
            current in ['i','I'] and previous in repeat_reference
        ) or ( # octavation
            (current == 'O' or current == operators.inverter) and previous == 'O'
        ) or ( # pedal mark 'up'
            current == 'p' and previous == 'p'
        ) or ( # rest prolongation
            current == operators.prolonger and /(\]~{0,2}$)|(\}~{0,1}$)/g.test(previous)
        ) or ( # error sign
            current == punctuation.bold_double_barline and previous == punctuation.bold_double_barline
        )
            stack.push (previous + current)
        else
            stack.push previous
            stack.push current

    return stack

parse = (expr) ->
    stack = tokenize expr
    tree = []
    current_key_signature = new KeySignature clefs['_'] #   this variable is the last defined key signature and affects all
    #                                                       succeeding note objects. If no key signature is yet defined when
    #                                                       a note is entered, the G-clef without accidentals is assumed.

    for token in stack
        if token == '\n'
            tree.push (new Newline)

        else if token in punctuation.splitters
            tree.push (new Splitter (get_splitter_length token))
            continue

        else if token.charAt(0) in key_symbols
            splitted_token = /^([\+_]+)((-*|=*)?)$/.exec(token)
            if (splitted_token != null and clefs[splitted_token[1]] != undefined)
                sign = if splitted_token[2].length == 0 then 0 else (if splitted_token[2].charAt(0) == '-' then -1 else 1)
                new_key_signature = splitted_token[2].length * sign
                
                tree.push (new KeySignature clefs[splitted_token[1]], new_key_signature)
                current_key_signature = new KeySignature clefs[splitted_token[1]], new_key_signature
                continue

        else if token.charAt(0) == punctuation.timesig
            if token.length == 3
                tree.push (new TimeSignature token.charAt(1), token.charAt(2))
            else if (token.length == 4 or token.length == 5)
                if /^(12)/.test(token.substring(1,token.length))
                    token_numerator = 12
                else
                    token_numerator = token.charAt(1)
                if /(16)$/.test(token)
                    token_denominator = 16
                else
                    token_denominator = token.charAt(token.length - 1)
                tree.push (new TimeSignature token_numerator, token_denominator)
            else
                tree.push (new ErrorSign)
            continue

        else if token == punctuation.barline
            tree.push (new MeasureEnd)
            continue

        else if token == punctuation.double_barline
            tree.push (new SectionEnd)
            continue

        else if token == punctuation.bold_double_barline
            tree.push (new End)
            continue

        else if token == punctuation.repeat_from
            tree.push (new RepeatFrom)
            continue

        else if token == punctuation.repeat_to
            tree.push (new RepeatTo)
            continue

        else if repetition[token] != undefined
            if typeof repetition[token] == 'number'
                tree.push (new RepeatSectionStart repetition[token])
            else
                tree.push (new RepeatSectionEnd)
            continue

        else if octavation[token] != undefined
            if typeof octavation[token] == 'number'
                tree.push (new OctavationStart)
            else
                tree.push (new OctavationEnd)
            continue

        else if token.charAt(0) in dynamics_symbols
            tree.push (new Dynamic dynamics[token])
            continue

        else if token.charAt(0) in gradual_dynamics_symbols
            tree.push (new GradualDynamic gradual_dynamics[token])
            continue

        else if token == navigation.coda
            tree.push (new Coda)
            continue

        else if token == navigation.segno
            tree.push (new Segno)
            continue

        else if token.charAt(0) in repeat_reference
            if token.length > 0
                tree.push (new FromTo references[token.charAt(0)], references[token.charAt(1)])
            else
                tree.push (new FromTo references[token])
            continue

        else if token == pedal.down
            tree.push (new PedalDown)
            continue

        else if token == pedal.up
            tree.push (new PedalUp)
            continue

        else if token == arpegio and (tree[tree.length - 1] instanceof Chord)
            tree[tree.length - 1].add_arpeggio()
            continue

        else if token == '..' and not (tree[tree.length - 1] instanceof Chord) # internally used to create beams between eighth notes
            tree.push (new ErrorSign)
            continue
        
        else if token.charAt(0) in rests
            for symbol in token
                if symbol == ']'
                    tree.push (new Rest 0)
                else if symbol == '}'
                    tree.push (new Rest 1)
                else
                    tree[tree.length - 1].increase_length_exponent()
            continue

        chord_notes = []

        for symbol in token
            try
                note_pitch = get_pitch symbol
                chord_notes.push (new Note note_pitch, current_key_signature)
            catch error
                if symbol == operators.prolonger
                    chord_notes[chord_notes.length - 1]
                        .increase_length_exponent()
                if (symbol == note_dot and chord_notes.length > 0)
                    chord_notes[chord_notes.length - 1]
                        .add_dot_length()
                if ((
                    symbol in accidentals_symbols or
                    symbol in articulations_symbols or
                    symbol in ornaments_symbols or
                    symbol == operators.inverter or # for the case of inverted ornamentation
                    symbol == accent_mark
                    ) and chord_notes.length > 0)
                    chord_notes[chord_notes.length - 1]
                        .add_diacritical_mark(symbol)

        if chord_notes.length > 0
            tree.push (new Chord chord_notes)

    return tree
