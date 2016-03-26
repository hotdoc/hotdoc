/*
 * CMark syntax extension for hotdoc smart includes
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

#include "cmark_include_extension.h"
#include "cmark_include_scanner.h"

static cmark_node *try_opening_include_block(cmark_syntax_extension *self,
                                          bool indented,
                                          cmark_parser *parser,
                                          cmark_node *parent,
                                          const char *input)
{
  cmark_node *ret = NULL;
  cmark_bufsize_t matched = scan_open_include_block(input,
      cmark_parser_get_first_nonspace(parser));

  printf ("Matched is %d\n", matched);

  return ret;
}

cmark_syntax_extension *cmark_include_extension_new(void) {
  cmark_syntax_extension *ext = cmark_syntax_extension_new("includes");

  ext->try_opening_block = try_opening_include_block;

  return ext;
}
