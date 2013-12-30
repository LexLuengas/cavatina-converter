# temporary test bench
(function($) {
	var sheet = new Sheet($('#container'));
	sheet.draw(); // item to draw (by hash key? by singleton?)
	sheet.forward(); // by pixels? by custom unit? by last drawn element?
})(jQuery);
