log_result = (string) ->
	$('#result').html string

update = ->
	tree = parse ($ 'textarea').val()
	log_result ((n.get_str() for n in tree).join "\n")

init = () ->
    $('textarea')
    	.keyup ->
    	    update()
    	.keydown ->
    	    update()
    	.keypress ->
    	    update()

$ -> init()
