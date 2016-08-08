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

#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "cmark_include_extension.h"
#include "cmark_include_scanner.h"

typedef struct
{
  CMarkIncludeResolveFunc resolve_func;
} include_private;

#define PRIV(ext) ((include_private *) ext->priv)

static cmark_node *try_opening_include_block(cmark_syntax_extension *self,
                                          bool indented,
                                          cmark_parser *parser,
                                          cmark_node *parent,
                                          const char *input)
{
  cmark_bufsize_t start, end;
  char *contents;
  const char *final_contents;
  cmark_strbuf *uri, *text;

  if (!PRIV(self)->resolve_func)
    goto done;

  start = scan_open_include_block(input,
      cmark_parser_get_first_nonspace(parser));

  if (!start)
    goto done;

  start += cmark_parser_get_first_nonspace(parser);

  text = cmark_strbuf_new(start);
  cmark_strbuf_put(text, (unsigned char *) input, start - 2);

  end = scan_close_include_block(input,
      cmark_parser_get_first_nonspace(parser));

  end += cmark_parser_get_first_nonspace(parser);

  uri = cmark_strbuf_new(end - start + 1);

  cmark_strbuf_put(uri, (unsigned char *) input + start, end - start);

  contents = PRIV(self)->resolve_func(cmark_strbuf_get(uri));

  if (contents) {
    cmark_strbuf_puts(text, contents);
    free(contents);
  } else {
    goto done;
  }

  cmark_strbuf_puts(text, input + end + 2);
  final_contents = cmark_strbuf_get(text);

  cmark_parser_advance_offset(parser, input, start, false);

  cmark_parser_feed_reentrant(parser, final_contents, strlen(final_contents));

  cmark_parser_advance_offset(parser, input, strlen(input), false);

  cmark_strbuf_free(uri);
  cmark_strbuf_free(text);

done:
  return NULL;
}

cmark_syntax_extension *cmark_include_extension_new(void)
{
  cmark_syntax_extension *ext = cmark_syntax_extension_new("includes");

  ext->try_opening_block = try_opening_include_block;
  ext->priv = calloc(1, sizeof(include_private));

  return ext;
}

void cmark_include_extension_set_resolve_function(
    cmark_syntax_extension *ext,
    CMarkIncludeResolveFunc func)
{
  PRIV(ext)->resolve_func = func;
}
