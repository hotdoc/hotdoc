/*
 * re2c syntax scanner for gtk-doc
 *
 * Copyright 2016 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2016 Collabora Ltd.
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

#include <stdlib.h>
#include <string.h>
#include "cmark_gtkdoc_scanner.h"

cmark_bufsize_t _ext_scan_at(cmark_bufsize_t (*scanner)(const unsigned char *),
	const char *s, cmark_bufsize_t offset)
{
	cmark_bufsize_t res;
	cmark_bufsize_t len = strlen(s);
	unsigned char *ptr = (unsigned char *)s;

        if (ptr == NULL || offset > len) {
          return 0;
        } else {
	  res = scanner(ptr + offset);
        }

	return res;
}

/*!re2c
  re2c:define:YYCTYPE  = "unsigned char";
  re2c:define:YYCURSOR = p;
  re2c:define:YYMARKER = marker;
  re2c:define:YYCTXMARKER = marker;
  re2c:yyfill:enable = 0;

  spacechar = [ \t\v\f];
  newline = [\r]?[\n];

  escaped_char = [\\][|!"#$%&'()*+,./:;<=>?@[\\\]^_`{}~-];
*/

// Scan an opening gtk-doc code block.
cmark_bufsize_t _scan_open_gtkdoc_code_block(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  [|][\[] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}

// Scan a language comment
cmark_bufsize_t _scan_language_comment(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  "<!-- language=\"" [^`\r\n\x00]* " -->" / [ \t]*[\r\n] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}

// Scan a closing gtk-doc code block.
cmark_bufsize_t _scan_close_gtkdoc_code_block(const unsigned char *p)
{
  const unsigned char *marker = NULL;
  const unsigned char *start = p;
/*!re2c
  [\]][|] { return (cmark_bufsize_t)(p - start); }
  .?                        { return 0; }
*/
}
