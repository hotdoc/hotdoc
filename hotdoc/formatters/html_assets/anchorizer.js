/*
 * anchorizer
 *
 * Copyright 2015 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2015 Collabora Ltd.
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * You should have received a copy of the GNU Lesser General Public
 * License along with this library; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301 USA
 */

$(document).ready(function() {
	var anchor_map = {};
	$("h1,h2,h3,h4,h5").each(function() {
		if ($(this).attr('id'))
			return;

    		var hyphenated = $(this).text().trim().replace(/\s/g,'-').toLowerCase();

		hyphenated = hyphenated.replace(/[!\"#$%&'\(\)\*\+,\.\/:;<=>\?\@\[\\\]\^`\{\|\}~]/g, '');

		var new_id = hyphenated;
		var counter = 0;
		while (($('#' + new_id).length)) {
			counter += 1;
			new_id = hyphenated + counter;
		}

		new_id = new_id.replace(/[^\x00-\x7F]/g, "");;
    		$(this).attr('id', new_id);
		anchor_map["#" + new_id] = $(this).text();
    	});

	$("a:empty").each(function() {
		var href = $(this).attr("href");
		if (href === undefined)
			return true;

		var text = anchor_map[href];
		if (text === undefined) {
			console.log("No local ref for empty link", href);
			return true;
		}

		$(this).text(text);
	});
});
