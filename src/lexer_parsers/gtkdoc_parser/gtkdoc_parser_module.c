#include <Python.h>
#include "comment_module_interface.h"
#include "parser.h"
#include "lexer.h"

yyscan_t my_scanner;

static PyObject *
parser_parse_comment_blocks (PyObject *self, PyObject *args)
{
  const char *raw_source;
  const char *filename;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "ss", &raw_source, &filename))
    return NULL;

  comment_module_set_current_filename (filename);

  YY_BUFFER_STATE state;

  if (yylex_init(&my_scanner)) {
    return NULL;
  }

  //yyset_debug (1, my_scanner);

  state = yy_scan_string(raw_source, my_scanner);

  yyset_lineno (1, my_scanner);

  if (yyparse(my_scanner, &ret)) {
    return NULL;
  }

  yy_delete_buffer(state, my_scanner);

  yylex_destroy(my_scanner);

  return ret;
}

static PyMethodDef ParserMethods[] = {
  {"parse_comment_blocks",  parser_parse_comment_blocks, METH_VARARGS, "Get parsed comment blocks"
    " from a source file"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initgtkdoc_parser(void)
{
  comment_module_init ();
  (void) Py_InitModule("gtkdoc_parser", ParserMethods);
}

