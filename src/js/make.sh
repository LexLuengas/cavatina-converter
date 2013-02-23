cat \
	src/symbols.coffee \
	src/semantics.coffee \
	src/structures.coffee \
	src/syntax.coffee \
	src/dom.coffee \
	> presto.coffee
coffee -c presto.coffee
