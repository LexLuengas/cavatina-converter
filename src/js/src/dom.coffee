init = () ->
    $('button').click ->
        tree = parse ($ 'textarea').val()


$ -> init()
