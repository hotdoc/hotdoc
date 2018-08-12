/*
 * Hotdoc python extension for fast retrieval of C code comments.
 *
 * Copyright 2015 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2015 Collabora Ltd.
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

#include "scanner.h"

struct module_state {
  PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
static struct module_state _state;
#endif

static PyObject *
scanner_extract_comments (PyObject *self, PyObject *args)
{
  PyObject *input;
  char *utf8;
  PyObject *list;

  if (!PyArg_ParseTuple(args, "O!", &PyUnicode_Type, &input))
    return NULL;

  utf8 = PyUnicode_AsUTF8(input);

  list = PyList_New (0);
  scan_comments (utf8, list);

  Py_INCREF (list);
  return list;
}

static PyMethodDef scanner_methods[] = {
  {"extract_comments",  scanner_extract_comments, METH_VARARGS, "Extract comments from string."},
  {NULL, NULL, 0, NULL}
};

#if PY_MAJOR_VERSION >= 3

static int scanner_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int scanner_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}


static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "c_comment_scanner",
        NULL,
        sizeof(struct module_state),
        scanner_methods,
        NULL,
        scanner_traverse,
        scanner_clear,
        NULL
};

#define INITERROR return NULL


PyMODINIT_FUNC
PyInit_c_comment_scanner(void)

#else
#define INITERROR return

PyMODINIT_FUNC
initc_comment_scanner(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
  PyObject *module = PyModule_Create(&moduledef);
#else
  PyObject *module = Py_InitModule("c_comment_scanner", scanner_methods);
#endif

  if (module == NULL)
    INITERROR;

#if PY_MAJOR_VERSION >= 3
  return module;
#endif
}

