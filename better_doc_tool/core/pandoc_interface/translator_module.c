#include <Python.h>
#include <dlfcn.h>

char * (*hs_markdown_to_json)(const char *);
char * (*hs_markdown_to_html)(const char *);
char * (*hs_json_to_html)(const char *);
char * (*hs_docbook_to_markdown)(const char *);

static PyObject *
markdown_to_json (PyObject *self, PyObject *args)
{
  const char *to_convert;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "s", &to_convert))
    return NULL;

  char *converted = hs_markdown_to_json (to_convert);

  ret = PyString_FromString (converted);
  free (converted);
  return ret;
}

static PyObject *
json_to_html (PyObject *self, PyObject *args)
{
  const char *to_convert;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "s", &to_convert))
    return NULL;

  char *converted = hs_json_to_html (to_convert);

  ret = PyString_FromString (converted);
  free (converted);
  return ret;
}

static PyObject *
markdown_to_html (PyObject *self, PyObject *args)
{
  const char *to_convert;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "s", &to_convert))
    return NULL;

  char *converted = hs_markdown_to_html (to_convert);

  ret = PyString_FromString (converted);
  free (converted);
  return ret;
}

static PyObject *
docbook_to_markdown (PyObject *self, PyObject *args)
{
  const char *to_convert;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "s", &to_convert))
    return NULL;

  char *converted = hs_docbook_to_markdown (to_convert);

  ret = PyString_FromString (converted);
  free (converted);
  return ret;
}

static PyMethodDef TranslatorMethods[] = {
  {"markdown_to_json",  markdown_to_json, METH_VARARGS, "Translate markdown to json"},
  {"json_to_html", json_to_html, METH_VARARGS, "Translate json to html"},
  {"markdown_to_html", markdown_to_html, METH_VARARGS, "Translate markdown to html"},
  {"docbook_to_markdown", docbook_to_markdown, METH_VARARGS, "Translate docbook to markdown"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
inittranslator(void)
{
  (void) Py_InitModule("translator", TranslatorMethods);
  PyObject *toplevel_module = PyImport_ImportModule ("better_doc_tool.core.main");
  PyObject *source_file = PyObject_GetAttrString (toplevel_module, "__file__");

  PyObject *path_module = PyImport_ImportModule("os.path");
  PyObject *basename_func = PyObject_GetAttrString (path_module, "dirname");
  PyObject *join_func = PyObject_GetAttrString (path_module, "join");
  void *libConvert;
  void (*translator_init)(void);
  PyObject *source_location = PyObject_CallFunction (basename_func, "O", source_file);
  PyObject *convert_lib = PyObject_CallFunction (join_func, "Os",
      source_location, "pandoc_interface/libConvert.so");

  if ( (libConvert = dlopen(PyString_AsString (convert_lib), RTLD_LAZY)) == NULL ||
       (translator_init = dlsym(libConvert, "doc_translator_init")) == NULL ||
       (hs_markdown_to_html = dlsym(libConvert, "hs_markdown_to_html")) == NULL ||
       (hs_json_to_html = dlsym(libConvert, "hs_json_to_html")) == NULL ||
       (hs_docbook_to_markdown = dlsym(libConvert, "hs_docbook_to_markdown")) == NULL ||
       (hs_markdown_to_json = dlsym(libConvert, "hs_markdown_to_json")) == NULL ) {
    return;
  }

  Py_DECREF (convert_lib);
  Py_DECREF (path_module);
  Py_DECREF (basename_func);
  Py_DECREF (join_func);
  Py_DECREF (toplevel_module);
  Py_DECREF (source_location);

  translator_init();
}

