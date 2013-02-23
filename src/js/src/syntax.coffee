get_octave = (symbol) ->
    for i in [0..octaves.length]
        if (octaves.charAt i) == symbol
            return i

    throw new InvalidSymbolError

get_splitter_length = (symbol) ->
    return splitter_length[symbol]

tokenize = (expr) ->
    tokens = []
    for char in expr
        if char == operators.special_splitter and
        tokens[tokens.length - 1] == operators.special_splitter
            tokens[tokens.length - 1] += char
        else
            tokens.push char
    return tokens

parse = (expr) ->
    tokens = tokenize expr
    stack = [[]]
    for token in tokens
        if token not in operators['splitters']
            stack[stack.length - 1].push token
        else
            stack[stack.length - 1] = stack[stack.length - 1].join('')
            stack.push token
            stack.push []

    stack[stack.length - 1] = stack[stack.length - 1].join('')

    tree = []

    for token in stack
        chord_notes = []
        if token in operators.splitters
            tree.push (new Splitter (get_splitter_length token))
        for symbol in token
            try
                chord_notes.push (new Note (get_octave symbol))
            catch error

        if chord_notes.length > 0
            tree.push (new Chord chord_notes)

    return tree
