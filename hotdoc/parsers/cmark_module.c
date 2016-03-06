#include <Python.h>
#include "cmark.h"
  
static PyObject *
markdown_to_html (PyObject *self, PyObject *args)
{
  PyObject *input;
  PyObject *utf8;
  char *output;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "O!", &PyUnicode_Type, &input))
    return NULL;

  utf8 = PyUnicode_AsUTF8String(input);
  output = cmark_markdown_to_html(PyString_AsString(utf8), PyObject_Length(utf8), 0);
  Py_DECREF(utf8);
  ret = PyUnicode_FromString(output);
  free(output);

  return ret;
}

static PyMethodDef ScannerMethods[] = {
  {"to_html",  markdown_to_html, METH_VARARGS, "Translate commonmark to html"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcmark(void)
{
  (void) Py_InitModule("cmark", ScannerMethods);
}
