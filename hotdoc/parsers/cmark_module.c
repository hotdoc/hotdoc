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

#include "cmark_module_utils.h"
#include "cmark.h"
#include "cmark_gtkdoc_extension.h"
#include "cmark_include_extension.h"

cmark_syntax_extension *cmark_table_extension_new();

static cmark_parser *gtkdoc_parser = NULL;
static cmark_syntax_extension *include_extension = NULL;
static cmark_syntax_extension *gtkdoc_extension = NULL;
static PyObject *include_resolver = NULL;
static PyObject *link_resolver = NULL;
static cmark_parser *hotdoc_parser = NULL;
static PyObject *diag_class = NULL;
static PyObject *diagnostics = NULL;
static PyObject *id_from_text_func = NULL;

void free_named_link(NamedLink *link) {
  if (link == NULL)
    return;

  free (link->title);
  free (link->ref);
  free (link);
}

typedef struct {
  cmark_llist *empty_links;
  cmark_node *root;
  bool lazy_loaded;
  cmark_node *page_title;
} CMarkDocument;

static NamedLink *
resolve_link(const char *id) {
  PyObject *link = NULL;
  PyObject *utf8 = NULL;
  PyObject *ref = NULL;
  PyObject *title = NULL;
  NamedLink *res = NULL;

  if (!link_resolver)
    goto done;

  link = PyObject_CallMethod(link_resolver, "get_named_link", "(s)", id);
  if (PyErr_Occurred()) {
    PyErr_Clear();
    goto done;
  }

  if (link != Py_None) {
    ref = PyObject_CallMethod(link, "get_link", NULL);

    if (PyErr_Occurred()) {
      PyErr_Clear();
      goto done;
    }

    title = PyObject_CallMethod(link, "get_title", NULL);
    if (PyErr_Occurred()) {
      PyErr_Clear();
      goto done;
    }

    res = calloc(1, sizeof(NamedLink));

    if (ref != Py_None) {
      utf8 = PyUnicode_AsUTF8String(ref);
      res->ref = strdup(PyString_AsString(utf8));
      Py_DECREF(utf8);
    }

    if (title != Py_None) {
      utf8 = PyUnicode_AsUTF8String(title);
      res->title = strdup(PyString_AsString(utf8));
      Py_DECREF(utf8);
    }
  }

done:
  Py_XDECREF(link);
  Py_XDECREF(ref);
  Py_XDECREF(title);
  return res;
}

void
diagnose(const char *code, const char *message, int lineno, int column) {
  PyObject *args;
  PyObject *diag;

  if (diagnostics == NULL)
    return;

  args = Py_BuildValue("ssii", code, message, lineno, column);
  diag = PyObject_CallObject(diag_class, args);
  if (PyErr_Occurred()) {
    PyErr_Print();
    PyErr_Clear();
    return;
  }
  PyList_Append(diagnostics, diag);
  Py_DECREF(args);
  Py_DECREF(diag);
}

static PyObject *
gtkdoc_to_ast(PyObject *self, PyObject *args) {
  CMarkDocument *doc;
  PyObject *input;
  PyObject *utf8;
  PyObject *cap;

  if (!PyArg_ParseTuple(args, "O!O", &PyUnicode_Type, &input, &link_resolver))
    return NULL;

  Py_XDECREF(diagnostics);
  diagnostics = PyList_New(0);

  doc = calloc(1, sizeof(CMarkDocument));

  cmark_gtkdoc_extension_set_link_resolve_function(gtkdoc_extension, resolve_link);

  utf8 = PyUnicode_AsUTF8String(input);
  cmark_parser_feed(gtkdoc_parser, PyString_AsString(utf8), PyObject_Length(utf8));
  Py_DECREF(utf8);

  doc->root = cmark_parser_finish(gtkdoc_parser);

  cap = PyCapsule_New((void *)doc, "cmark.document", NULL);

  return Py_BuildValue("OO", cap, diagnostics);
}

static char *
resolve_include(const char *uri) {
  PyObject *contents;
  char *res = NULL;

  if (!include_resolver) {
    return NULL;
  }

  contents = PyObject_CallMethod(include_resolver, "resolve", "s", uri);

  if (PyUnicode_Check(contents)) {
    PyObject *old_contents;

    old_contents = contents;
    contents = PyUnicode_AsUTF8String(old_contents);
    Py_DECREF(old_contents);
  }

  if (contents != Py_None)
    res = strdup(PyString_AsString(contents));

  Py_DECREF(contents);

  return res;
}

static void collect_title(CMarkDocument *doc)
{
  cmark_node *tmp = cmark_node_first_child(doc->root);

  while (tmp) {
    cmark_node *next = cmark_node_next(tmp);

    if (cmark_node_get_type(tmp) == CMARK_NODE_HEADING) {
      doc->page_title = tmp;
      break;
    }

    tmp = next;
  }
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
      if (PyErr_Occurred()) {
        PyErr_Clear();
        continue;
      }
      tmp_ret = PyUnicode_Concat(ret, tmp);
      Py_DECREF(ret);
      Py_DECREF(tmp);
      ret = tmp_ret;
    }
  }

  cmark_iter_free(iter);

  return ret;
}

static void
collect_autorefs(cmark_parser *parser) {
  cmark_node *root = cmark_parser_get_root(parser);
  cmark_node *tmp = cmark_node_first_child(root);

  while (tmp) {
    cmark_node *next = cmark_node_next(tmp);

    if (cmark_node_get_type(tmp) == CMARK_NODE_HEADING) {
      PyObject *translated;
      PyObject *utf8 = concatenate_title(tmp);
      char *title = PyString_AsString(utf8);

      if (title != NULL) {
        translated = PyObject_CallFunction(id_from_text_func, "(sb)", title, Py_True);
        cmark_parser_add_reference(parser, title, PyString_AsString(translated), NULL);
        Py_DECREF(translated);
      }

      Py_DECREF(utf8);
    }

    tmp = next;
  }
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

  collect_autorefs(hotdoc_parser);

  doc->root = cmark_parser_finish(hotdoc_parser);

  collect_title(doc);

  ret = PyCapsule_New((void *)doc, "cmark.document", NULL);

  return ret;
}

static char *render_doc(CMarkDocument *doc)
{
  cmark_event_type ev_type;

  if (doc->lazy_loaded == false) {
    cmark_iter *iter;

    iter = cmark_iter_new(doc->root);
    while ((ev_type = cmark_iter_next(iter)) != CMARK_EVENT_DONE) {
      cmark_node *cur = cmark_iter_get_node(iter);
      if (ev_type == CMARK_EVENT_ENTER && cmark_node_get_type(cur) == CMARK_NODE_LINK) {
        NamedLink *named_link;
        const char *url = cmark_node_get_url(cur);

        if (url[0] == '\0')
          continue;

        named_link = resolve_link(url);
        if (!named_link) {
          cmark_strbuf *message = cmark_strbuf_new(0);
          cmark_strbuf_puts(message, "Trying to link to non-existing identifier ‘");
          cmark_strbuf_puts(message, url);
          cmark_strbuf_puts(message, "’");
          diagnose("markdown-bad-link", cmark_strbuf_get(message), -1, -1);
          continue;
        }

        if (cmark_node_first_child(cur) == NULL) {
          cmark_node *label = cmark_node_new(CMARK_NODE_TEXT);
          cmark_node_append_child(cur, label);

          doc->empty_links = cmark_llist_append(doc->empty_links, cur);

          cmark_node_set_user_data(cur, strdup(url));
          cmark_node_set_user_data_free_func(cur, free);

          if (named_link->ref)
            cmark_node_set_url(cur, named_link->ref);

          if (named_link->title)
            cmark_node_set_literal(label, named_link->title);
        } else if (named_link->ref) {
            cmark_node_set_url(cur, named_link->ref);
        }

        free_named_link(named_link);
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
      NamedLink *named_link = resolve_link(id);

      if (!named_link) {
        continue;
      }

      if (named_link->ref)
        cmark_node_set_url(cur, named_link->ref);

      if (named_link->title)
        cmark_node_set_literal(label, named_link->title);

      free_named_link(named_link);
    }
  }

  return cmark_render_html(doc->root, 0);
}

static PyObject *
ast_to_html(PyObject *self, PyObject *args) {
  PyObject *cap;
  PyObject *ret;
  CMarkDocument *doc;
  char *out;

  PyArg_ParseTuple(args, "O!O", &PyCapsule_Type, &cap, &link_resolver);

  doc = PyCapsule_GetPointer(cap, "cmark.document");

  if (doc == NULL)
    return NULL;

  Py_XDECREF(diagnostics);
  diagnostics = PyList_New(0);

  out = render_doc(doc);

  ret = PyUnicode_FromString(out);

  free(out);

  return Py_BuildValue("OO", ret, diagnostics);
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
update_subpage_links(PyObject *self, PyObject *args) {
  PyObject *cap;
  PyObject *links;

  PyArg_ParseTuple(args, "O!O!", &PyCapsule_Type, &cap, &PySet_Type, &links);

  Py_INCREF(Py_None);
  return Py_None;
}

static PyMethodDef ScannerMethods[] = {
  {"gtkdoc_to_ast",  gtkdoc_to_ast, METH_VARARGS, "Translate gtk-doc syntax to an opaque AST"},
  {"hotdoc_to_ast", hotdoc_to_ast, METH_VARARGS, "Translate hotdoc syntax to an opaque AST"},
  {"title_from_ast", ast_get_title, METH_VARARGS, "Get the first title in an opaque AST"},
  {"update_subpage_links", update_subpage_links, METH_VARARGS, "Update subpage links in opaque AST"},
  {"ast_to_html",  ast_to_html, METH_VARARGS, "Translate an opaque AST to html"},
  {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcmark(void)
{
  PyObject *exception_mod = PyImport_ImportModule("hotdoc.parsers.cmark_utils");
  PyObject *utils_mod = PyImport_ImportModule("hotdoc.utils.utils");
  (void) Py_InitModule("cmark", ScannerMethods);
  cmark_init();
  cmark_syntax_extension *ptables_ext = cmark_table_extension_new();

  diag_class = PyObject_GetAttrString(exception_mod, "CMarkDiagnostic");
  id_from_text_func = PyObject_GetAttrString(utils_mod, "id_from_text");

  include_extension = cmark_include_extension_new();
  gtkdoc_extension = cmark_gtkdoc_extension_new();

  gtkdoc_parser = cmark_parser_new(0);
  cmark_parser_attach_syntax_extension(gtkdoc_parser, gtkdoc_extension);

  hotdoc_parser = cmark_parser_new(CMARK_OPT_NORMALIZE);
  cmark_parser_attach_syntax_extension(hotdoc_parser, include_extension);
  cmark_parser_attach_syntax_extension(gtkdoc_parser, include_extension);

  /* Who doesn't want tables, seriously ? */
  if (ptables_ext) {
    cmark_parser_attach_syntax_extension(gtkdoc_parser, ptables_ext);
    cmark_parser_attach_syntax_extension(hotdoc_parser, ptables_ext);
  }
}
