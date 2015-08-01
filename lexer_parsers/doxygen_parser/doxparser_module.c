#include "doxparser.h"

static DoxParser *parser;

static PyObject *
parser_parse_comment_block (PyObject *self, PyObject *args)
{
  const char *raw_comment;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "s", &raw_comment))
    return NULL;

  ret = dox_parser_parse (parser, raw_comment);

  return ret;
}

static PyMethodDef ParserMethods[] = {
  {"parse_comment_block",  parser_parse_comment_block, METH_VARARGS, "Get a parsed comment block"
    " from a raw comment"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initdoxygen_parser(void)
{
  parser = dox_parser_new();
  (void) Py_InitModule("doxygen_parser", ParserMethods);
}

