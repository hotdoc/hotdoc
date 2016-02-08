$(document).ready(function() {
	$("h1,h2,h3,h4,h5").each(function() {
		if ($(this).attr('id'))
			return;

    		var hyphenated = $(this).text().replace(/\s/g,'-').toLowerCase();
    		$(this).attr('id',hyphenated);
    	});
});
