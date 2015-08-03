#include <Python.h>

void create_comment_block (PyObject **block,
                           char *name,
                           PyObject *annotations,
                           PyObject *parameters,
                           PyObject *description,
                           PyObject *tags);
void comment_module_init  (void);
PyObject *create_annotation    (char *name, PyObject *arg);
PyObject *create_tag    (char *name, char *value, PyObject *description, PyObject *annotations);
PyObject *create_parameter (char *name, PyObject *description, PyObject *annotations);
