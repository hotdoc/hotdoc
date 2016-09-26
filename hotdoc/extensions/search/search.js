/*
 * Search hook for hotdoc's search extension.
 *
 * Copyright 2015,2016 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2015,2016 Collabora Ltd.
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

var trie = undefined;
var head = document.getElementsByTagName('head')[0];
var script = document.createElement('script');
script.type = 'text/javascript';
script.onload = function() {
	trie = new Trie(trie_data, true);
	console.log("loaded trie, testing", trie.lookup_node("abecedary"));
}
script.src = 'trie_index.js';
head.appendChild(script);

function dirname(path) {
	return path.replace(/\\/g, '/')
		.replace(/\/[^\/]*\/?$/, '');
}

function getSortedKeys(obj) {
	var keys = []; for(var key in obj) keys.push(key);
	return keys.sort(function(a,b){return obj[a]-obj[b]});
}

document.getElementById("lookup").onkeyup=function () {
	if (trie === undefined) {
		return;
	}

	var result_area = document.getElementById('result_area');
	var new_html = '';
	var results = [];

	var query = this.value

	if (query.length == 0) {
		result_area.innerHTML = new_html;
		return;
	}

	console.time('lookup');

	var node = trie.lookup_node (query);

	if (node != null && node.is_final) {
		results.push (query);
		new_html += '<p>Found exact match</p>';
	} else if (node != null) {
		var completions = trie.lookup_completions(node, 5);
		for (idx in completions) {
			results.push(completions[idx].get_word());
		}
		new_html += '<p>Found some completions</p>';
	} else if (query.length > 3) {
		var submatches = trie.lookup_submatches(query, 5);

		if (submatches.length > 0) {
			new_html += '<p>Found some submatches</p>';
			for (idx in submatches) {
				results.push(submatches[idx].get_word());
			}
		}

		if (submatches.length < 5) {
			var corrections = trie.search(query, 2);
			var sorted_keys = getSortedKeys(corrections);

			if (sorted_keys.length) {
				new_html += '<p>Did you mean ?</p>';
			} else {
				new_html += '<p>Nothing relevant found</p>';
			}

			for (idx in sorted_keys) {
				var word = sorted_keys[idx];
				results.push(word);
			}
		}
	}

	console.timeEnd('lookup');

	new_html += '<ul>';

	for (idx in results) {
		var result = results[idx];

		new_html += '<li>' + result + '</li>';
	}

	new_html += '</ul>';

	result_area.innerHTML = new_html;
};
