#include <Python.h>

static PyObject *comment_block_class;
static PyObject *annotation_class;
static PyObject *tag_class;
static PyObject *parameter_class;
static char     *current_filename;

void
create_comment_block (PyObject **block, char *name, PyObject *annotations, PyObject *parameters,
    PyObject *description, PyObject *tags)
{
  PyObject *arglist = Py_BuildValue ("(ssOOOO)", name, current_filename, annotations, parameters, description, tags);

  *block = PyObject_CallObject(comment_block_class, arglist);

  Py_DECREF (parameters);
  Py_DECREF (arglist);
  Py_DECREF (annotations);
  Py_DECREF (description);
  Py_DECREF (tags);
}

PyObject *
create_annotation (char *name, PyObject *arg)
{
  PyObject *res;

  PyObject *arglist = Py_BuildValue ("(sO)", name, arg);
  res = PyObject_CallObject(annotation_class, arglist);
  Py_DECREF (arg);
  Py_DECREF (arglist);

  return res;
}

PyObject *
create_parameter (char *name, PyObject *description, PyObject *annotations)
{
  PyObject *arglist = Py_BuildValue ("(sOO)", name, annotations, description);
  PyObject *res;

  res = PyObject_CallObject(parameter_class, arglist);

  Py_DECREF (annotations);
  Py_DECREF (description);
  Py_DECREF (arglist);

  return res;
}

PyObject *
create_tag (char *name, char *value, PyObject *description, PyObject *annotations)
{
  PyObject *res;

  PyObject *arglist = Py_BuildValue ("(ssOO)", name, value, annotations, description);
  res = PyObject_CallObject(tag_class, arglist);
  Py_XDECREF (annotations);
  Py_XDECREF (description);
  Py_DECREF (arglist);

  return res;
}

void
comment_module_set_current_filename (const char *filename)
{
  if (current_filename)
    free (current_filename);
  current_filename = strdup (filename);
}

void
comment_module_init (void)
{
  PyObject *comment_module = PyImport_ImportModule("better_doc_tool.core.comment_block");
  comment_block_class = PyObject_GetAttrString (comment_module, "GtkDocCommentBlock");
  annotation_class = PyObject_GetAttrString (comment_module, "GtkDocAnnotation");
  tag_class = PyObject_GetAttrString (comment_module, "GtkDocTag");
  parameter_class = PyObject_GetAttrString (comment_module, "GtkDocParameter");
  current_filename = NULL;
}
