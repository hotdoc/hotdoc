/*
 * Hotdoc extension for CMark
 *
 * Copyright 2016 Mathieu Duponchelle <mathieu.duponchelle@opencredd.com>
 * Copyright 2016 Collabora Ltd.
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

#include <Python.h>

#include "cmark.h"
#include "cmark_gtkdoc_extension.h"
#include "cmark_include_extension.h"

static cmark_parser *gtkdoc_parser = NULL;
static cmark_parser *hotdoc_parser = NULL;

typedef struct {
  cmark_llist *empty_links;
  cmark_node *root;
  bool lazy_loaded;
} CMarkDocument;

static PyObject *
gtkdoc_to_ast(PyObject *self, PyObject *args) {
  CMarkDocument *doc;
  PyObject *input;
  PyObject *link_resolver;
  PyObject *utf8;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "O!O", &PyUnicode_Type, &input, &link_resolver))
    return NULL;

  doc = calloc(1, sizeof(CMarkDocument));

  utf8 = PyUnicode_AsUTF8String(input);
  cmark_parser_feed(gtkdoc_parser, PyString_AsString(utf8), PyObject_Length(utf8));
  Py_DECREF(utf8);

  doc->root = cmark_parser_finish(gtkdoc_parser);

  ret = PyCapsule_New((void *)doc, "cmark.document", NULL);

  return ret;
}

static PyObject *
hotdoc_to_ast(PyObject *self, PyObject *args) {
  CMarkDocument *doc;
  PyObject *input;
  PyObject *utf8;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "O!O", &PyUnicode_Type, &input))
    return NULL;

  doc = calloc(1, sizeof(CMarkDocument));

  utf8 = PyUnicode_AsUTF8String(input);
  cmark_parser_feed(hotdoc_parser, PyString_AsString(utf8), PyObject_Length(utf8));
  Py_DECREF(utf8);

  doc->root = cmark_parser_finish(hotdoc_parser);

  ret = PyCapsule_New((void *)doc, "cmark.document", NULL);

  return ret;
}

static char *render_doc(CMarkDocument *doc, PyObject *link_resolver)
{
  cmark_event_type ev_type;

  if (doc->lazy_loaded == false) {
    cmark_iter *iter;

    iter = cmark_iter_new(doc->root);
    while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
        cmark_node *cur = cmark_iter_get_node(iter);
        if (ev_type == CMARK_EVENT_ENTER && cmark_node_get_type(cur) == CMARK_NODE_LINK) {
          const char *url = cmark_node_get_url(cur);

          if (cmark_node_first_child(cur) == NULL && url[0] != '\0') {
            PyObject *link;
            cmark_node *label = cmark_node_new(CMARK_NODE_TEXT);
            cmark_node_append_child(cur, label);

            link = PyObject_CallMethod(link_resolver, "get_named_link", "s", url);
            if (link != Py_None) {
              PyObject *ref = PyObject_CallMethod(link, "get_link", NULL);
              PyObject *title = PyObject_CallMethod(link, "get_title", NULL);

              doc->empty_links = cmark_llist_append(doc->empty_links, cur);

              cmark_node_set_user_data(cur, strdup(url)); 
              cmark_node_set_user_data_free_func(cur, free);

              if (ref != Py_None) {
                cmark_node_set_url(cur, PyString_AsString(ref));
              }

              if (title != Py_None)
                cmark_node_set_literal(label, PyString_AsString(title));
              else
                cmark_node_set_literal(label, url);

              cmark_node_append_child(cur, label);
              Py_DECREF(title);
              Py_DECREF(ref);
            } else {
              cmark_node_set_literal(label, url);
            }
            Py_DECREF(link);
          }
        }
    }

    cmark_iter_free(iter);
    doc->lazy_loaded = true;
  } else {
    cmark_llist *tmp;

    for (tmp = doc->empty_links; tmp; tmp = tmp->next) {
      cmark_node *cur = (cmark_node *) tmp->data;
      char *id = (char *) cmark_node_get_user_data(cur);
      cmark_node *label = cmark_node_first_child(cur);
      PyObject *link;

      link = PyObject_CallMethod(link_resolver, "get_named_link", "s", id);

      if (link != Py_None) {
        PyObject *ref = PyObject_CallMethod(link, "get_link", NULL);
        PyObject *title = PyObject_CallMethod(link, "get_title", NULL);

        if (title != Py_None)
          cmark_node_set_literal(label, PyString_AsString(title));

        if (ref != Py_None)
          cmark_node_set_url(cur, PyString_AsString(ref));

        Py_DECREF(title);
        Py_DECREF(ref);
      } else {
        cmark_node_set_literal(label, id);
      }
      Py_DECREF(link);
    }
  }

  return cmark_render_html(doc->root, 0);
}

static PyObject *
ast_to_html(PyObject *self, PyObject *args) {
  PyObject *cap;
  PyObject *ret;
  PyObject *link_resolver;
  CMarkDocument *doc;
  char *out;

  PyArg_ParseTuple(args, "O!O", &PyCapsule_Type, &cap, &link_resolver);

  doc = PyCapsule_GetPointer(cap, "cmark.document");

  out = render_doc(doc, link_resolver);

  ret = PyUnicode_FromString(out);

  free(out);

  return ret;
}

static PyMethodDef ScannerMethods[] = {
  {"gtkdoc_to_ast",  gtkdoc_to_ast, METH_VARARGS, "Translate gtk-doc syntax to an opaque AST"},
  {"hotdoc_to_ast", hotdoc_to_ast, METH_VARARGS, "Translate hotdoc syntax to an opaque AST"},
  {"ast_to_html",  ast_to_html, METH_VARARGS, "Translate an opaque AST to html"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcmark(void)
{
  (void) Py_InitModule("cmark", ScannerMethods);
  cmark_init();
  cmark_syntax_extension *ptables_ext = cmark_find_syntax_extension("piped-tables");

  gtkdoc_parser = cmark_parser_new(0);
  cmark_parser_attach_syntax_extension(gtkdoc_parser,
      cmark_gtkdoc_extension_new());

  hotdoc_parser = cmark_parser_new(0);
  cmark_parser_attach_syntax_extension(hotdoc_parser,
      cmark_include_extension_new());

  /* Who doesn't want tables, seriously ? */
  if (ptables_ext)
    cmark_parser_attach_syntax_extension(gtkdoc_parser, ptables_ext);
}
