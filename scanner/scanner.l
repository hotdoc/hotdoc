
%{
#include "scanner.h"

extern int yylex (PyObject *comments, const char *filename);
#define YY_DECL int yylex (PyObject *comments, const char *filename)
static int yywrap (void);
static void parse_comment ();
%}

%option nounput
%option yylineno

%%

"/*"              { parse_comment (comments, filename); }

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

#define BUFSIZE 64

static void
parse_comment (PyObject *comments, const char *filename)
{
  int c1, c2;
  int comment_lineno;
  int cursor;

  c1 = input();
  c2 = input();

  comment_lineno = yylineno - 1;
  if (c2 != EOF && (c1 == '*' && c2 != '*' && c2 != '/')) {
    char *comment = (char *) malloc(sizeof(char) * 3);
    char buf[BUFSIZE];
    cursor = 0;

    comment[0] = '/';
    comment[1] = '*';
    comment[2] = '\0';
    while (c2 != EOF && !(c1 == '*' && c2 == '/'))
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

    PyObject *item = Py_BuildValue ("(ssii)", comment,
    				    strdup(filename), /* Sic .. */
                                    comment_lineno,
                                    yylineno);
    PyList_Append (comments, item);
  } else {
    while (c2 != EOF && !(c1 == '*' && c2 == '/'))
      {
        c1 = c2;
        c2 = input();
      }

    return;
  }
}

int
scan_filename (const char *filename, PyObject *comments)
{
  yylineno = 1;
  yyin = fopen (filename, "r");

  yylex (comments, filename);

  fclose (yyin);

  return 0;
}
