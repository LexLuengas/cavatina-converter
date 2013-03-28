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
            (
                previous.charAt(Math.max 0, previous.length - 2) in octaves or
                previous.charAt(previous.length - 1) in octaves
            )
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
