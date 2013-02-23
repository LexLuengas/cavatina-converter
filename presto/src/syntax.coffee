get_octave = (symbol) ->
    for i in [0..octaves.length]
        if (octaves.charAt i) == symbol
            return (i + 1)

    throw new InvalidOctaveSymbolError

tokenize = (expr) ->
    return expr.split ''

parse = (expr) ->
    tokens = tokenize expr
    stack = [[]]
    for token in tokens
        if !(token in operators['splitters'])
            stack[stack.length - 1].push token

    tree = []

    for part in stack
        chord_notes = []
        for symbol in part
            try
                chord_notes.push (new Note (get_octave symbol))
            catch error
                console.log "ignored #{symbol}"
        tree.push (new Chord chord_notes)
        console.log (tree[tree.length - 1].get_str())
