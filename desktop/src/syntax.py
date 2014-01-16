
#--- SYNTAX ---#       

def get_stringPosition(index, stack, expr):
    if len(stack[index]) > 1:
        return expr.index(stack[index])
    
    prevLen = 0
    for s in stack[:index]:
        prevLen += len(s)
    return prevLen
    
class SyntaxException(SyntaxError): # shows error position
    def __init__(self, infoList):
        i, stack, expr = infoList
        errorIndex = get_stringPosition(i, stack, expr)
        left = max(errorIndex - 10, 0)
        right = min(errorIndex + 11, len(expr))
        token = stack[i]
        message = 'Invalid input \'{}\' at position {}:\t{} {} {}\n{}'.format(
            token,
            errorIndex,
            "..." if errorIndex - 10 > 0 else "   ",
            expr[left:right],
            "..." if errorIndex + 11 < len(expr) else "   ",
            " "*(47 + len(str(errorIndex)) + len(token)) + "\t    " + " "*(errorIndex - left) + "^")
        SyntaxError.__init__(self, message)
        
def get_pitch(symbol):
    for i in range(len(note_range)):
        if note_range[i] == symbol:
            return i
    
    raise InvalidSymbolError

def get_splitter_length(symbol):
    return splitter_length[symbol]

def tokenize(expr):
    if len(expr) <= 1:
        return [expr]

    stack = [expr[0]]

    for current in expr[1:]:
        previous = stack.pop()
        # -- group all contextually linked symbols
        if ( # new line
            current == 'n' and previous == '\\'
        ) or ( # quarter space
            current == punctuation['special_splitter'] and
            previous == punctuation['special_splitter']
        ) or ( # double barline
            current == punctuation['barline'] and
            previous == punctuation['barline']
        ) or ( # long barlines
            (
                current == '\\' and (previous in simple_punctuation or previous == ',\\')
            ) or (
                current == ',' and previous == ',\\'
            )
        ) or ( # C-clef
            (current == key_symbols[0] and previous == key_symbols[1]) or
            (current == key_symbols[1] and previous == key_symbols[0])
        ) or ( # key signature
            previous[0] in clefs and
            current in accidentals_symbols and
            (not re.search('-|=',previous) or len(re.findall('-|=', previous)) < 7) and
            (
                previous[-1] in clefs or
                (current == accidentals_symbols[0] and previous[-1] == accidentals_symbols[0]) or
                (current == accidentals_symbols[1] and previous[-1] == accidentals_symbols[1])
            )
        ) or ( # time signature
            (
                (
                    len(previous) <= 2 and
                    previous[0] == time_signature and
                    current in digits
                ) or ( # case 12 is numumerator or 16 is denominator
                    len(previous) == 3 and
                    re.search('^(12)|(16)$', previous[1:] + current)
                ) or (
                    previous == '~121' and current == '6'
                ) or ( # common time and cut-time
                    previous == time_signature and
                    current == 'c'
                ) or (
                    previous[-1] == 'c' and
                    current == operators['prolonger']
                )
            ) and (
                len(stack) > 0 and (
                stack[-1][0] in clefs or
                stack[-1] in [
                    punctuation['barline'],
                    punctuation['barline'],
                    punctuation['double_barline'],
                    punctuation['bold_double_barline']
                ])
            )
        ) or ( # chords
            current in chord_set and previous[0] in chord_set
        ) or ( # altered notes
            (   (current in all_diacritics) or
                (current == operators['prolonger'] and not re.search('~[-=\'\"<>\[\{`]*~', previous)) or # no more than 2 '~' for each note
                (current == operators['inverter'] and re.search('[^\[](\[|\{)$', previous)) or # inverted ornaments
                (current == '[' and (re.search('[^\[]\[{1,5}$', previous) or not re.search('\[', previous)) and not re.search('\{', previous)) or # mordent, trills, no double ornamentation
                (current == '{' and not re.search('\[|\{', previous)) or # grupetto, no double ornamentation
                (current == '.' and not re.search('\.\.', previous)) or # beams
                (current == operators['inverter'] and not re.search('`[-=\'\"<>\[\{~]*`', previous)) # stem inversion
            ) and (
                previous[0] in note_range
            )
        ) or ( # dynamics
            (current in dynamics_symbols or current == operators['inverter']) and (previous[0] in dynamics_symbols) and ((previous + current) in dynamics)
        ) or ( # gradual dynamics: crescendo, long form
            current == 'l' and previous == 'l'
        ) or ( # repeats
            (current == 'o' or current == operators['inverter']) and previous[0] == 'o'
        ) or ( # repeat references with indications
            current in ['i','I'] and previous in repeat_reference
        ) or ( # octavation
            (current == 'O' or current == operators['inverter']) and previous == 'O'
        ) or ( # pedal mark 'up'
            current == 'p' and previous == 'p'
        ) or ( # rest prolongation
            (current == operators['prolonger'] and re.search('(\]~{0,2}$)|(\}~{0,1}$)', previous)) or
            (current == note_dot and re.search('(\]~{0,3}$)|(\}~{0,2}$)', previous)) or
            (current == rests[0] and previous == rests[0])
        ) or ( # beam errors
            current == '.' and previous == '.'
        ) or ( # error sign
            current == punctuation['bold_double_barline'] and previous == punctuation['bold_double_barline']
        ):
            stack.append(previous + current)
        else:
            stack.append(previous)
            stack.append(current)
        
    return stack

def parse(expr):
    stack = tokenize(expr)
    tree = []
    current_key_signature = KeySignature(clefs['+']) #   this variable is the last defined key signature and affects all
    #                                                       succeeding note objects. If no key signature is yet defined when
    #                                                       a note is entered, the G-clef without accidentals is assumed.

    for tokenIndex, token in enumerate(stack):
        if token == '\n':
            tree.append(Newline())
            continue

        elif token in punctuation['splitters']:
            tree.append(Splitter( get_splitter_length(token) ))
            continue

        elif token[0] in key_symbols:
            split_token = re.search(r'^([\+_]{1,2})([-|=]*)', token)
            if (split_token and split_token.group(1) in clefs):
                sign =  0 if not split_token.group(2) else ( \
                        -1 if split_token.group(2)[0] == '-' else \
                        1)#   split_token.group(2)[0] == '='
                new_key_signature = sign * len(split_token.group(2))
                tree.append( KeySignature(clefs[split_token.group(1)], new_key_signature) )
                current_key_signature = KeySignature(clefs[split_token.group(1)], new_key_signature)
                continue

        elif token[0] == time_signature:
            if len(token) <= 3:
                if token[1] == 'c':
                    tree.append( TimeSignature(common_time[token[1:]]) )
                else:
                    tree.append( TimeSignature(token[1], token[2]) )
            elif (len(token) == 4 or len(token) == 5):
                if re.search('^12', token[1:]):
                    token_numerator = 12
                else:
                    token_numerator = token[1]
                if re.search('16$',token):
                    token_denominator = 16
                else:
                    token_denominator = token[-1]
                tree.append( TimeSignature(token_numerator, token_denominator) )
            else:
                tree.append( ErrorSign() )
            continue

        elif token == punctuation['barline']:
            tree.append( MeasureEnd() )
            continue

        elif token == punctuation['double_barline']:
            tree.append( SectionEnd() )
            continue

        elif token == punctuation['bold_double_barline']:
            tree.append( End() )
            continue

        elif token == punctuation['repeat_from']:
            tree.append( RepeatFrom() )
            continue

        elif token == punctuation['repeat_to']:
            tree.append( RepeatTo() )
            continue
        
        elif token == punctuation['long']['systemic_barline']:
            tree.append( SystemicBarline() )
            continue
        
        elif token == punctuation['long']['grand_staff']:
            tree.append( GrandStaff() )
            continue
            
        elif token == punctuation['long']['systemic_barline']:
            tree.append( SystemicBarline() )
            continue
            
        elif token in punctuation['long']['double_systemic_barline']:
            tree.append( DoubleSystemicBarline() )
            continue
            
        elif token == punctuation['long']['bold_systemic_barline']:
            tree.append( BoldSystemicBarline() )
            continue
            
        elif token == punctuation['long']['long_repeat_from']:
            tree.append( LongRepeatFrom() )
            continue
            
        elif token == punctuation['long']['long_repeat_to']:
            tree.append( LongRepeatTo() )
            continue

        elif token in repetition:
            if repetition[token] == 'end':
                tree.append( RepeatSectionEnd() )
            else:
                tree.append( RepeatSectionStart(repetition[token]) )
            continue

        elif token in octavation:
            if type(octavation[token]) is int:
                tree.append ( OctavationStart(octavation[token]) )
            else:
                tree.append( OctavationEnd() )
            continue

        elif token[0] in dynamics_symbols:
            tree.append ( Dynamic(dynamics[token]) )
            continue

        elif token[0] in gradual_dynamics_symbols:
            tree.append ( GradualDynamic(gradual_dynamics[token]) )
            continue

        elif token == navigation['coda']:
            tree.append( Coda() )
            continue

        elif token == navigation['segno']:
            tree.append( Segno() )
            continue

        elif token[0] in repeat_reference:
            if len(token) > 1:
                tree.append( FromTo(references[token[0]], references[token[1]]) )
            else:
                tree.append( FromTo(references[token]) )
            continue

        elif token == pedal['down']:
            tree.append( PedalDown() )
            continue

        elif token == pedal['up']:
            tree.append( PedalUp() )
            continue

        elif token == arpegio and isinstance(tree[-1], Chord):
            tree[-1].add_arpeggio()
            continue

        elif token == '..': # internally used to create beams between eighth notes
            tree.append( ErrorSign() )
            continue
        
        elif token[0] in rests:
            if token[:2] == ']]': # implicit prolongation
                tree.append ( Rest(1) )
                token = token[2:]
                
            for symbol in token:
                if symbol == ']':
                    tree.append ( Rest(0) )
                elif symbol == '}':
                    tree.append ( Rest(1) )
                elif symbol == note_dot:
                    tree[-1].add_dot_length()
                elif symbol == operators['prolonger']:
                    tree[-1].increase_length_exponent()
            continue

        chord_notes = []

        for symbolIndex, symbol in enumerate(token):
            beamed = False
            try:
                note_pitch = get_pitch(symbol)
                if note_pitch >= eighth_note_range: # quarter notes
                    chord_notes.append( Note(note_pitch, current_key_signature, length_exponent=1) )
                else: # eighth notes
                    chord_notes.append( Note(note_pitch, current_key_signature, length_exponent=0) )
                
            except InvalidSymbolError:
                if symbol == operators['prolonger']:
                    chord_notes[-1].increase_length_exponent()
                elif symbol == note_dot and len(chord_notes) > 0:
                    chord_notes[-1].add_dot_length()
                elif symbol == '.':
                    beamed = True
                elif ((symbol in accidentals_symbols or
                    symbol in articulations_symbols or
                    symbol in ornaments_symbols or
                    (symbol == operators['inverter'] and token[symbolIndex-1] in ornaments_symbols) or # for the case of inverted ornamentation
                    symbol == accent_mark
                    ) and len(chord_notes) > 0):
                    chord_notes[-1].add_diacritical_mark(symbol)
                elif symbol == operators['inverter']: # stem inversion
                    chord_notes[-1].invertStem()
                elif symbol in simple_punctuation:
                    pass
                else:
                    raise SyntaxException([tokenIndex, stack, expr])
        
        if len(chord_notes) > 0:
            tree.append( Chord(chord_notes, beamed) )
        else:
            raise SyntaxException([tokenIndex, stack, expr])

    return tree
