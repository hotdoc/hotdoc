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

typedef struct
{
  CMarkGtkDocLinkResolveFunc link_resolve_func;
} gtkdoc_private;

#define PRIV(ext) ((gtkdoc_private *) ext->priv)

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

typedef struct
{
  cmark_inline_parser *parser;
  int allow_dashes;
} ParsingContext;

static int is_valid_c(int c, int pos, ParsingContext *context) {
  return (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == '_';
}

static int is_valid_symbol_name(int c, int pos, ParsingContext *context) {
  if (is_valid_c(c, pos, context))
    return 1;

  if (c == ':' || c == '-' || c == '.') {
    char nc = cmark_inline_parser_peek_at(context->parser, pos + 1);

    if (c == ':')
      context->allow_dashes = 1;
    else if (c == '-' && !context->allow_dashes)
      return 0;

    return (nc && is_valid_symbol_name(nc, pos + 1, context));
  }
  return 0;
}

static int is_valid_c_or_dbus(ParsingContext *context, int c, int pos) {
  if (is_valid_c(c, pos, context))
    return 1;


  if (c == '.') {
    char nc = cmark_inline_parser_peek_at(context->parser, pos + 1);

    if (!nc || is_valid_c(nc, pos + 1, context))
      return 0;

    if (pos > 0) {
      nc = cmark_inline_parser_peek_at(context->parser, pos - 1);
      return is_valid_c(nc, pos + 1, context);
    }

    return 1;
  }

  return 0;
}

static void translate_sourcepos(cmark_node *parent, unsigned long col,
                                int *actual_line, int *actual_col) {
  const char *contents = cmark_node_get_string_content(parent);
  *actual_line = cmark_node_get_start_line(parent);
  *actual_col = cmark_node_get_start_column(parent);
  unsigned long tmp_col = 0;

  if (strlen(contents) < col)
    return;

  while (tmp_col++ < col) {
    *actual_col += 1;
    if (contents[tmp_col] == '\n') {
      *actual_col = 0;
      *actual_line += 1;
    }
  }
}

static cmark_node *get_first_parent_block(cmark_node *node) {
  cmark_node *parent = node;

  while (cmark_node_get_type(parent) > CMARK_NODE_LAST_BLOCK) {
    parent = cmark_node_parent(parent);
  }

  return parent;
}

static cmark_node *fixup_nodes(cmark_syntax_extension *self,
                               cmark_parser *parser,
                               cmark_inline_parser *inline_parser,
                               cmark_node *parent,
                               int start_offset,
                               int size)
{
  int node_text_len;
  cmark_node *prev = NULL;
  cmark_node *tmp;
  int name_size = size;
  cmark_strbuf *name;
  NamedLink *named_link;

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

  named_link = PRIV(self)->link_resolve_func(cmark_strbuf_get(name));

  if (!named_link || !named_link->ref) {
    int actual_line, actual_col;

    translate_sourcepos(get_first_parent_block(parent),
        start_offset, &actual_line, &actual_col);

    cmark_strbuf *message = cmark_strbuf_new(0);
    cmark_strbuf_puts(message, "Trying to link to non-existing symbol ‘");
    cmark_strbuf_puts(message, cmark_strbuf_get(name));
    cmark_strbuf_puts(message, "’");
    diagnose("gtk-doc-bad-link", cmark_strbuf_get(message), actual_line - 1,
        actual_col - 1);
    cmark_strbuf_free(message);
    cmark_node_set_literal(prev, cmark_strbuf_get(name));
    cmark_strbuf_free(name);
    return prev;
  }

  free_named_link(named_link);

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
  int tmp_pos;
  ParsingContext context;

  context.parser = inline_parser;
  context.allow_dashes = 0;

  offset = cmark_inline_parser_get_offset(inline_parser);

  if (offset == 0)
    goto done;

  if (cmark_inline_parser_peek_at(inline_parser, offset + 1) != ')')
    goto done;

  start = offset - 1;

  if (!is_valid_c_or_dbus(&context, cmark_inline_parser_peek_at(inline_parser, start),
        cmark_inline_parser_get_offset(inline_parser)))
    goto done;

  while (start >= 0) {
    unsigned char c = cmark_inline_parser_peek_at(inline_parser, start);

    if (is_valid_c_or_dbus(&context, c, cmark_inline_parser_get_offset(inline_parser))) {
      start -= 1;
    } else {
      break;
    }
  }

  ret = fixup_nodes(self, parser, inline_parser, parent, start + 1, offset - start - 1);

  if (!ret)
    goto done;

  tmp_pos = cmark_inline_parser_get_offset (inline_parser);
  tmp_delim = cmark_inline_parser_get_last_delimiter(inline_parser);

  while (tmp_delim) {
    delimiter *prev = tmp_delim->previous;
    tmp_pos -= tmp_delim->length;

    if (tmp_pos < start + 1) {
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
  ParsingContext context;

  context.parser = inline_parser;
  context.allow_dashes = 0;

  prev_char = cmark_inline_parser_peek_at(
      inline_parser,
      cmark_inline_parser_get_offset(inline_parser) - 1);

  if (prev_char && prev_char != ' ' && prev_char != '\t' && prev_char != '\n')
    return NULL;

  cmark_inline_parser_advance_offset(inline_parser);
  param_name = cmark_inline_parser_take_while(inline_parser,
      (CMarkInlinePredicate) is_valid_c, &context);

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
  cmark_node *link = NULL;
  char *symbol_name = NULL;
  NamedLink *named_link = NULL;
  int start_offset = cmark_inline_parser_get_offset(inline_parser);
  ParsingContext context;

  context.parser = inline_parser;
  context.allow_dashes = 0;

  if (start_offset > 0) {
    char prev_char = cmark_inline_parser_peek_at(
        inline_parser,
        start_offset - 1);

    if (prev_char && prev_char != ' ' && prev_char != '\t' && prev_char != '\n')
      return NULL;
  }

  cmark_inline_parser_advance_offset(inline_parser);

  symbol_name = cmark_inline_parser_take_while(inline_parser,
      (CMarkInlinePredicate) is_valid_symbol_name, &context);

  if (!symbol_name)
    goto done;

  named_link = PRIV(self)->link_resolve_func(symbol_name);
  if (!named_link || !named_link->ref) {
    int actual_line, actual_col;

    translate_sourcepos(get_first_parent_block(parent),
        start_offset, &actual_line, &actual_col);
    cmark_strbuf *message = cmark_strbuf_new(0);
    cmark_strbuf_puts(message, "Trying to link to non-existing symbol ‘");
    cmark_strbuf_puts(message, symbol_name);
    cmark_strbuf_puts(message, "’");
    diagnose("gtk-doc-bad-link", cmark_strbuf_get(message), actual_line - 1, actual_col - 1);
    cmark_strbuf_free(message);
    link = cmark_node_new (CMARK_NODE_TEXT);
    cmark_node_set_literal (link, symbol_name);
  } else {
    link = cmark_node_new(CMARK_NODE_LINK);
  }

  cmark_node_set_url(link, symbol_name);

done:
  free(symbol_name);
  free_named_link(named_link);

  return link;
}

static cmark_node *gtkdoc_match(cmark_syntax_extension *self,
                                cmark_parser *parser,
                                cmark_node *parent,
                                unsigned char character,
                                cmark_inline_parser *inline_parser)
{
  if (PRIV(self)->link_resolve_func == NULL)
    return NULL;

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
  cmark_bufsize_t first_nonspace = cmark_parser_get_first_nonspace(parser);
  cmark_bufsize_t matched = scan_close_gtkdoc_code_block(input, first_nonspace);

  if (matched) {
    cmark_parser_advance_offset(parser, input, matched + first_nonspace, false);

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

void cmark_gtkdoc_extension_set_link_resolve_function(
    cmark_syntax_extension *ext,
    CMarkGtkDocLinkResolveFunc func)
{
  PRIV(ext)->link_resolve_func = func;
}

cmark_syntax_extension *cmark_gtkdoc_extension_new(void) {
  cmark_syntax_extension *ext = create_gtkdoc_extension();

  ext->priv = calloc(1, sizeof(gtkdoc_private));
  return ext;
}

bool init_libgtkdocextension(cmark_plugin *plugin) {
  cmark_plugin_register_syntax_extension(plugin, create_gtkdoc_extension());
  return true;
}
