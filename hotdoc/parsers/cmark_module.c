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
static cmark_syntax_extension *include_extension = NULL;
static PyObject *include_resolver = NULL;
static cmark_parser *hotdoc_parser = NULL;

typedef struct {
  cmark_llist *empty_links;
  cmark_node *root;
  bool lazy_loaded;
  cmark_llist *symbol_names;
  cmark_node *page_title;
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

static char *
resolve_include(const char *uri) {
  PyObject *contents;
  char *res;

  if (!include_resolver) {
    return NULL;
  }

  contents = PyObject_CallMethod(include_resolver, "resolve", "s", uri);

  res = PyString_AsString(contents);

  Py_DECREF(contents);

  return res;
}

static bool filter_item(CMarkDocument *doc, cmark_node *item_first_child) {
  cmark_node *para_first_child;
  cmark_node *label;

  if (cmark_node_get_type(item_first_child) != CMARK_NODE_PARAGRAPH)
    return false;

  para_first_child = cmark_node_first_child(item_first_child);

  if (!para_first_child)
    return false;

  if (cmark_node_next(para_first_child))
    return false;

  if (cmark_node_get_type(para_first_child) != CMARK_NODE_LINK)
    return false;

  /* Even with no url, this will return the empty string */
  if (cmark_node_get_url(para_first_child)[0])
    return false;

  label = cmark_node_first_child(para_first_child);

  if (!label)
    return false;

  /* Should not happen, text nodes are consolidated */
  if (cmark_node_next(label))
    return false;

  /* Should not happen, let's check anyway */
  if (cmark_node_get_type(label) != CMARK_NODE_TEXT)
    return false;

  /* We have found a symbol name */
  doc->symbol_names = cmark_llist_append(doc->symbol_names,
    strdup(cmark_node_get_literal(label)));

  return true;
}

static void filter_list(CMarkDocument *doc, cmark_node *list)
{
  cmark_event_type ev_type;
  cmark_iter *iter;

  iter = cmark_iter_new(list);
  while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
    cmark_node *cur = cmark_iter_get_node(iter);

    if (cur == list)
      continue;

    if (cmark_node_get_type(cur) == CMARK_NODE_ITEM)
      continue;

    /* We only check top level item contents */
    cmark_iter_reset(iter, cur, CMARK_EVENT_EXIT);

    if (filter_item(doc, cur)) {
      cmark_node_unlink(cmark_node_parent(cur));
    }
  }
  cmark_iter_free(iter);
}

static void filter_symbol_names(CMarkDocument *doc)
{
  cmark_event_type ev_type;
  cmark_iter *iter;

  iter = cmark_iter_new(doc->root);

  while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
    cmark_node *cur = cmark_iter_get_node(iter);

    if (cur == doc->root)
      continue;

    /* We only check top level elements */
    cmark_iter_reset(iter, cur, CMARK_EVENT_EXIT);

    if (cmark_node_get_type(cur) != CMARK_NODE_LIST)
      continue;

    filter_list(doc, cur);
  }

  cmark_iter_free(iter);
}

static void collect_title_and_subpage_links(CMarkDocument *doc)
{
  cmark_event_type ev_type;
  cmark_iter *iter;

  iter = cmark_iter_new(doc->root);

  while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
    cmark_node *cur = cmark_iter_get_node(iter);

    if (ev_type != CMARK_EVENT_ENTER)
      continue;

    if (!doc->page_title && cmark_node_get_type(cur) == CMARK_NODE_HEADING) {
      doc->page_title = cur;
    }

    if (cmark_node_get_type(cur) != CMARK_NODE_LINK)
      continue;
  }

  cmark_iter_free(iter);
}

static PyObject *
hotdoc_to_ast(PyObject *self, PyObject *args) {
  CMarkDocument *doc;
  PyObject *input;
  PyObject *utf8;
  PyObject *ret;

  if (!PyArg_ParseTuple(args, "O!O", &PyUnicode_Type, &input, &include_resolver))
    return NULL;

  doc = calloc(1, sizeof(CMarkDocument));

  cmark_include_extension_set_resolve_function(include_extension,
      resolve_include);

  utf8 = PyUnicode_AsUTF8String(input);
  cmark_parser_feed(hotdoc_parser, PyString_AsString(utf8), PyObject_Length(utf8));
  Py_DECREF(utf8);

  doc->root = cmark_parser_finish(hotdoc_parser);

  filter_symbol_names(doc);

  collect_title_and_subpage_links(doc);

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

static PyObject *concatenate_title(cmark_node *title_node) {
  cmark_event_type ev_type;
  cmark_iter *iter;
  PyObject *tmp_ret;
  PyObject *ret = PyUnicode_FromString("");

  iter = cmark_iter_new(title_node);

  while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
    cmark_node *cur = cmark_iter_get_node(iter);
    const char *content;
    PyObject *tmp;

    if (ev_type != CMARK_EVENT_ENTER)
      continue;

    content = cmark_node_get_string_content(cur);
    if (content) {
      tmp = PyUnicode_FromString(content);
      tmp_ret = PyUnicode_Concat(ret, tmp);
      Py_DECREF(ret);
      Py_DECREF(tmp);
      ret = tmp_ret;
    }
  }

  cmark_iter_free(iter);

  return ret;
}

static PyObject *
ast_get_title(PyObject *self, PyObject *args) {
  PyObject *cap;
  CMarkDocument *doc;
  PyObject *ret;

  PyArg_ParseTuple(args, "O!", &PyCapsule_Type, &cap);

  doc = PyCapsule_GetPointer(cap, "cmark.document");

  if (doc->page_title) {
    ret = concatenate_title(doc->page_title);
  } else {
    ret = Py_None;
    Py_INCREF(Py_None);
  }

  return ret;
}

static PyObject *
symbol_names_in_ast(PyObject *self, PyObject *args) {
  PyObject *cap;
  PyObject *ret;
  CMarkDocument *doc;
  cmark_llist *tmp;

  PyArg_ParseTuple(args, "O!", &PyCapsule_Type, &cap);

  doc = PyCapsule_GetPointer(cap, "cmark.document");

  ret = PyList_New(0);

  for (tmp = doc->symbol_names; tmp; tmp = tmp->next) {
    PyList_Append(ret, PyString_FromString((char *)tmp->data));
  }

  return ret;
}

static PyObject *
update_subpage_links(PyObject *self, PyObject *args) {
  PyObject *cap;
  PyObject *links;
  CMarkDocument *doc;

  PyArg_ParseTuple(args, "O!O!", &PyCapsule_Type, &cap, &PySet_Type, &links);

  doc = PyCapsule_GetPointer(cap, "cmark.document");

  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef ScannerMethods[] = {
  {"gtkdoc_to_ast",  gtkdoc_to_ast, METH_VARARGS, "Translate gtk-doc syntax to an opaque AST"},
  {"hotdoc_to_ast", hotdoc_to_ast, METH_VARARGS, "Translate hotdoc syntax to an opaque AST"},
  {"title_from_ast", ast_get_title, METH_VARARGS, "Get the first title in an opaque AST"},
  {"symbol_names_in_ast", symbol_names_in_ast, METH_VARARGS, "Retrieve symbol names from opaque AST"},
  {"update_subpage_links", update_subpage_links, METH_VARARGS, "Update subpage links in opaque AST"},
  {"ast_to_html",  ast_to_html, METH_VARARGS, "Translate an opaque AST to html"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcmark(void)
{
  (void) Py_InitModule("cmark", ScannerMethods);
  cmark_init();
  cmark_syntax_extension *ptables_ext = cmark_find_syntax_extension("piped-tables");

  include_extension = cmark_include_extension_new();

  gtkdoc_parser = cmark_parser_new(0);
  cmark_parser_attach_syntax_extension(gtkdoc_parser,
      cmark_gtkdoc_extension_new());

  hotdoc_parser = cmark_parser_new(CMARK_OPT_NORMALIZE);
  cmark_parser_attach_syntax_extension(hotdoc_parser, include_extension);

  /* Who doesn't want tables, seriously ? */
  if (ptables_ext)
    cmark_parser_attach_syntax_extension(gtkdoc_parser, ptables_ext);
}
