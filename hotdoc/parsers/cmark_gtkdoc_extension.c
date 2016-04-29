/*
 * CMark syntax extension for gtk-doc
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cmark_gtkdoc_extension.h"
#include "cmark_gtkdoc_scanner.h"

static char *
my_strndup (const char *s, size_t n)
{
  char *result;
  size_t len = strlen (s);

  if (n < len)
    len = n;

  result = (char *) malloc (len + 1);
  if (!result)
    return 0;

  result[len] = '\0';
  return (char *) memcpy (result, s, len);
}

static int is_valid_c(int c) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
}

static int is_valid_symbol_name(int c) {
  return is_valid_c(c) || c == ':';
}

static cmark_node *fixup_nodes(cmark_inline_parser *inline_parser,
                                  cmark_node *parent,
                                  int size)
{
  int node_text_len;
  cmark_node *prev = NULL;
  cmark_node *tmp;
  int name_size = size;
  cmark_strbuf *name;

  for (prev = cmark_node_last_child(parent); prev; prev = cmark_node_previous(prev)) {
    if (cmark_node_get_type(prev) == CMARK_NODE_TEXT) {
      const char *text = cmark_node_get_literal(prev);
      node_text_len = strlen(text);
      size -= node_text_len;

      if (size <= 0) {
        if (size < 0) {
          char *split_text = my_strndup(text, size * -1);
          cmark_node *split = cmark_node_new(CMARK_NODE_TEXT);

          cmark_node_set_literal(split, split_text);
          free(split_text);

          split_text = my_strndup(text + (size * - 1), node_text_len - size);
          cmark_node_set_literal(prev, split_text);
          free(split_text);

          cmark_node_insert_before(prev, split);
        }
        break;
      }
    } else {
      return NULL;
    }
  }

  name = cmark_strbuf_new(name_size + 1);

  tmp = prev;

  while (tmp) {
    cmark_node *next = cmark_node_next(tmp);

    cmark_strbuf_puts(name, cmark_node_get_literal(tmp));
    if (tmp != prev)
      cmark_node_free(tmp);
    tmp = next;
  }

  cmark_node_set_type(prev, CMARK_NODE_LINK);
  cmark_node_set_url(prev, cmark_strbuf_get(name));

  cmark_strbuf_free(name);

  return prev;
}

static cmark_node *function_link_match(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_node *parent,
                                cmark_inline_parser *inline_parser)
{
  cmark_node *ret = NULL;
  delimiter *tmp_delim;
  int offset;
  int start;

  offset = cmark_inline_parser_get_offset(inline_parser);

  if (offset == 0)
    goto done;

  if (cmark_inline_parser_peek_at(inline_parser, offset + 1) != ')')
    goto done;

  start = offset - 1;

  if (!is_valid_c(cmark_inline_parser_peek_at(inline_parser, start)))
    goto done;

  while (start >= 0) {
    unsigned char c = cmark_inline_parser_peek_at(inline_parser, start);

    if (is_valid_c(c)) {
      start -= 1;
    } else {
      break;
    }
  }

  ret = fixup_nodes(inline_parser, parent, offset - start - 1);

  if (!ret)
    goto done;

  tmp_delim = cmark_inline_parser_get_last_delimiter(inline_parser);

  while (tmp_delim) {
    delimiter *prev = tmp_delim->previous;

    if (tmp_delim->position < start + 1) {
      break;
    }

    cmark_inline_parser_remove_delimiter(inline_parser, tmp_delim);
    tmp_delim = prev;
  }

  cmark_inline_parser_advance_offset(inline_parser);
  cmark_inline_parser_advance_offset(inline_parser);

done:
  return ret;
}

static cmark_node *param_ref_match(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_node *parent,
                                cmark_inline_parser *inline_parser) {
  cmark_node *emph, *text_node;
  char *param_name;
  char prev_char;

  prev_char = cmark_inline_parser_peek_at(
      inline_parser,
      cmark_inline_parser_get_offset(inline_parser) - 1);

  if (prev_char && prev_char != ' ' && prev_char != '\t' && prev_char != '\n')
    return NULL;

  cmark_inline_parser_advance_offset(inline_parser);
  param_name = cmark_inline_parser_take_while(inline_parser,
      (CMarkInlinePredicate) is_valid_c);

  if (!param_name)
    return NULL;

  emph = cmark_node_new(CMARK_NODE_EMPH);
  text_node = cmark_node_new(CMARK_NODE_TEXT);
  cmark_node_append_child(emph, text_node);

  cmark_node_set_literal(text_node, param_name);
  free(param_name);
  return emph;
}

static cmark_node *symbol_link_match(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_node *parent,
                                cmark_inline_parser *inline_parser) {
  cmark_node *link;
  char *symbol_name;

  if (cmark_inline_parser_get_offset(inline_parser) > 0) {
    char prev_char = cmark_inline_parser_peek_at(
        inline_parser,
        cmark_inline_parser_get_offset(inline_parser) - 1);

    if (prev_char && prev_char != ' ' && prev_char != '\t' && prev_char != '\n')
      return NULL;
  }

  cmark_inline_parser_advance_offset(inline_parser);

  symbol_name = cmark_inline_parser_take_while(inline_parser,
      (CMarkInlinePredicate) is_valid_symbol_name);

  if (!symbol_name)
    return NULL;

  link = cmark_node_new(CMARK_NODE_LINK);

  cmark_node_set_url(link, symbol_name);
  free(symbol_name);

  return link;
}

static cmark_node *gtkdoc_match(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_node *parent,
                                unsigned char character,
                                cmark_inline_parser *inline_parser)
{
  if (character == '(')
    return function_link_match(self, parser, parent, inline_parser);
  else if (character == '@')
    return param_ref_match(self, parser, parent, inline_parser);
  else if (character == '#' || character == '%')
    return symbol_link_match(self, parser, parent, inline_parser);
  return NULL;
}

static delimiter *gtkdoc_unused(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_inline_parser *inline_parser,
                                delimiter *opener,
                                delimiter *closer)
{
  return NULL;
}

static cmark_node *try_opening_code_block(cmark_syntax_extension *self,
                                          bool indented,
                                          cmark_parser *parser,
                                          cmark_node *parent,
                                          const char *input)
{
  cmark_node *ret = NULL;
  cmark_bufsize_t matched = scan_open_gtkdoc_code_block(input,
      cmark_parser_get_first_nonspace(parser));

  if (!indented && matched) {
    ret = cmark_parser_add_child(parser, parent,
        CMARK_NODE_CODE_BLOCK, cmark_parser_get_offset(parser));
    cmark_node_set_syntax_extension(ret, self);
    cmark_node_set_fenced(ret, true, 2,
        cmark_parser_get_first_nonspace(parser) - cmark_parser_get_offset(parser),
        0);
    cmark_parser_advance_offset(parser, input, matched, false);

    matched = scan_language_comment(input, matched);
    if (matched) {
      cmark_strbuf *lang = cmark_strbuf_new(32);
      cmark_strbuf_put(lang, (unsigned char *) input + 17, matched - 20);
      /* Will be transformed to fence info */
      cmark_node_set_string_content(ret, cmark_strbuf_get(lang));
      cmark_strbuf_free(lang);
      cmark_parser_advance_offset(parser, input, matched, false);
    }

  }

  return ret;
}

static bool code_block_matches(cmark_syntax_extension *self,
                          cmark_parser * parser,
                          const char   * input,
                          cmark_node   * parent)
{
  cmark_bufsize_t matched = scan_close_gtkdoc_code_block(input,
      cmark_parser_get_first_nonspace(parser));

  if (matched) {
    cmark_parser_advance_offset(parser, input, strlen(input) - 1, false);
    return false;
  }
  return true;
}

static cmark_syntax_extension *create_gtkdoc_extension(void) {
  cmark_syntax_extension *ext = cmark_syntax_extension_new("gtk_doc");

  ext->try_opening_block = try_opening_code_block;
  ext->last_block_matches = code_block_matches;
  ext->match_inline = gtkdoc_match;
  ext->insert_inline_from_delim = gtkdoc_unused;
  ext->special_inline_chars = cmark_llist_append(ext->special_inline_chars,
      (void *) '(');
  ext->special_inline_chars = cmark_llist_append(ext->special_inline_chars,
      (void *) '@');
  ext->special_inline_chars = cmark_llist_append(ext->special_inline_chars,
      (void *) '#');
  ext->special_inline_chars = cmark_llist_append(ext->special_inline_chars,
      (void *) '%');

  return ext;
}

cmark_syntax_extension *cmark_gtkdoc_extension_new(void) {
  return create_gtkdoc_extension();
}

bool init_libgtkdocextension(cmark_plugin *plugin) {
  cmark_plugin_register_syntax_extension(plugin, create_gtkdoc_extension());
  return true;
}
