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
        ) or ( # time signature
            previous.length < 3 and
            previous.charAt(0) == punctuation.timesig and
            current in digits and
            (keys[stack[stack.length - 1]] != undefined or
                stack[stack.length - 1] in [
                    punctuation.barline,
                    punctuation.barline,
                    punctuation.double_barline,
                    punctuation.bold_double_barline
                ]
            )
        ) or ( # chords
            current in chord_set and previous.charAt(0) in chord_set
        ) or ( # lengthened notes
            current == operators.prolonger and
            (
                previous.charAt(Math.max 0, previous.length - 2) in range or #? Esto es para el caso de doble '~'?
                previous.charAt(previous.length - 1) in range
            )
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
            tree.push (new Newline)

        else if token in punctuation.splitters
            tree.push (new Splitter (get_splitter_length token))
            continue

        else if keys[token] != undefined
            tree.push (new Key keys[token])
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

        else if token.charAt(0) == punctuation.timesig
            if token.length == 3
                tree.push (new TimeSignature token.charAt(1), token.charAt(2))
            else
                tree.push (new ErrorSign)
            continue

        chord_notes = []

        for symbol in token
            try
                chord_notes.push (new Note (get_pitch symbol))
            catch error
                if symbol == operators.prolonger
                    chord_notes[chord_notes.length - 1]
                        .increase_length_exponent()

        if chord_notes.length > 0
            tree.push (new Chord chord_notes)

    return tree
