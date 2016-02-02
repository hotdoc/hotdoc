$(document).ready(function() {
	var column_index = 0;
	var since_index = -1;

	$('#symbols tfoot th').each( function () {
		var title = $('#symbols thead th').eq( $(this).index() ).text();
		if (title == "Since") {
			since_index = column_index;
		} else {
			$(this).html( '<input type="text" placeholder="Search '+title+'" />' );
		}
		column_index += 1;
	} );

	// DataTable
	var table = $('#symbols').DataTable({
			"order": [[ 0, "asc" ]]
	});

	if (since_index != -1) {
		table.column (since_index).visible(false);
	}

	// Apply the search
	table.columns().every( function () {
		var that = this;

		if (this.index() != since_index) {
			$( 'input', this.footer() ).on( 'keyup change', function () {
				if ( that.search() !== this.value ) {
					that
						.search( this.value )
						.draw();
				}
			} );
		} else {
			$( 'input', this.footer() ).on( 'keyup change', function () {
				table.draw();
			} );
		}
	} );

	$('#filter_comparator').change( function() {
		table.draw();
	} );
	$('#filter_value').keyup( function() {
		table.draw(); 
	} );

	function compareVersions(v1, comparator, v2) {
		"use strict";
		comparator = comparator == '=' ? '==' : comparator;
		var v1parts = v1.split('.'), v2parts = v2.split('.');
		var maxLen = Math.max(v1parts.length, v2parts.length);
		var part1, part2;
		var cmp = 0;
		for(var i = 0; i < maxLen && !cmp; i++) {
			part1 = parseInt(v1parts[i], 10) || 0;
			part2 = parseInt(v2parts[i], 10) || 0;
			if(part1 < part2)
				cmp = 1;
			if(part1 > part2)
				cmp = -1;
		}
		return eval('0' + comparator + cmp);
	}

	$.fn.dataTableExt.afnFiltering.push(
			function( oSettings, aData, iDataIndex ) {
				if (since_index == -1) {
					return true;
				}

				var comparator = $('#filter_comparator').val();
				var value = $('#filter_value').val();
				var row_data = aData[since_index];

				if (value.length > 0) {
					switch (comparator) {

						case 'eq':
							return compareVersions (row_data, '==', value);
							break;
						case 'gt':
							return compareVersions (row_data, '>=', value);
							break;
						case 'lt':
							return compareVersions (row_data, '<=', value);
							break;
						case 'ne':
							return compareVersions (row_data, '!=', value);
							break;
					}

				}

				return true;
			}
	);
} );
