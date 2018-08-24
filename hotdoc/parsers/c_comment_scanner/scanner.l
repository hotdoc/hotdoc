/* -*- Mode: C -*-
 * GObject introspection: C lexer
 *
 * Copyright (c) 1997 Sandro Sigala  <ssigala@globalnet.it>
 * Copyright (c) 2007-2008 Jürg Billeter  <j@bitron.ch>
 * Copyright (c) 2010 Andreas Rottmann <a.rottmann@gmx.at>
 *
 * All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions
 * are met:
 * 1. Redistributions of source code must retain the above copyright
 *    notice, this list of conditions and the following disclaimer.
 * 2. Redistributions in binary form must reproduce the above copyright
 *    notice, this list of conditions and the following disclaimer in the
 *    documentation and/or other materials provided with the distribution.
 *
 * THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
 * IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
 * OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
 * IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
 * INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 * NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
 * DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
 * THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 * THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

%{
#include "scanner.h"

extern int yylex (PyObject *comments);
#define YY_DECL int yylex (PyObject *comments)
static int yywrap (void);
static int parse_comment ();
static int parse_define ();
%}

%option nounput
%option yylineno

HASH    #
SPACE   [ \t]

%%

"/*"                            { return parse_comment (comments);}
{HASH}{SPACE}*"define"{SPACE}*  { return parse_define (comments); }

.|\n		  { }

%%

static int
yywrap (void)
{
  return 1;
}

static char *
realloc_and_concat(char *str, char *s2)
{
    int len = 0;
    char *s;

    if (str != NULL)
        len = strlen(str);

    len += (strlen(s2) + 1) * sizeof(*s2);
    s = realloc(str, len);
    strcat(s, s2);
    return s;
}

#define BUFSIZE 1024

static int
parse_define (PyObject *comments)
{
  int c = input();
  int include_next_line = 0;
  char *define = strdup("#define ");
  char buf[BUFSIZE];
  int cursor = 0;
  int define_lineno = yylineno - 1;

  while (c > 0) {
    buf[cursor++] = c;

    if (cursor >= BUFSIZE - 1) {
      buf[cursor] = 0;
      define = realloc_and_concat (define, buf);
      cursor = 0;
    }

    c = input();
    if (c == '\\') {
      include_next_line = !include_next_line;
    } else if (c == '\n') {
      if (!include_next_line)
        break;
      include_next_line = 0;
    } else if (c != ' ' && c != '\t') {
      include_next_line = 0;
    }
  }

  buf[cursor] = 0;
  define = realloc_and_concat (define, buf);

  PyObject *item = Py_BuildValue ("(siii)",
        define,
        define_lineno,
        yylineno,
        0);
  PyList_Append (comments, item);

  if (c <= 0)
    return 0;
  return 1;
}

static int
parse_comment (PyObject *comments)
{
  int c1, c2;
  int comment_lineno;
  int cursor;

  c1 = input();

  if (c1 <= 0)
    return 0;

  c2 = input();

  comment_lineno = yylineno - 1;
  if (c2 > 0 && (c1 != '/' && c2 != '*' && c2 != '/')) {
    char *comment = (char *) malloc(sizeof(char) * 3);
    char buf[BUFSIZE];
    cursor = 0;

    comment[0] = '/';
    comment[1] = '*';
    comment[2] = '\0';
    while (c2 > 0 && !(c1 == '*' && c2 == '/'))
    {
      buf[cursor++] = c1;

      if (cursor >= BUFSIZE - 1) {
        buf[cursor] = 0;
        comment = realloc_and_concat (comment, buf);
        cursor = 0;
      }

      c1 = c2;
      c2 = input();
    }

    buf[cursor] = 0;
    comment = realloc_and_concat (comment, buf);
    comment = realloc_and_concat (comment, "*/");

    PyObject *item = Py_BuildValue ("(siii)", comment,
        comment_lineno,
        yylineno,
        1);
    PyList_Append (comments, item);
  } else {
    while (c2 > 0 && !(c1 == '*' && c2 == '/'))
    {
      c1 = c2;
      c2 = input();
    }
  }

  if (c2 <= 0)
    return 0;
  return 1;
}

int
scan_comments (const char *contents, PyObject *comments)
{
  yylineno = 1;

  yy_scan_string(contents);

  while (yylex (comments));

  return 0;
}
