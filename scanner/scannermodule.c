#include "scanner.h"

static PyObject *
scanner_get_comments (PyObject *self, PyObject *args)
{
  const char *filename;
  PyObject *list;

  if (!PyArg_ParseTuple(args, "s", &filename))
    return NULL;

  list = PyList_New (0);
  scan_filename (filename, list);

  Py_INCREF (list);
  return list;
}

static PyMethodDef ScannerMethods[] = {
  {"get_comments",  scanner_get_comments, METH_VARARGS, "Get comments from a filename."},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initscanner(void)
{
  (void) Py_InitModule("scanner", ScannerMethods);
}

