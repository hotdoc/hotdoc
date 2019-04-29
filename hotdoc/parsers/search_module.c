#include <Python.h>
#include <glib.h>
#include <json-glib/json-glib.h>
#include <libxml/HTMLparser.h>
#include <libxml/xpath.h>
#include <string.h>

#include "trie.h"

struct module_state
{
  PyObject *error;
};

typedef struct
{
  struct trie *trie;
  GHashTable *stop_words;
  GMutex url_lock;
  GMutex fragment_lock;
  GMutex trie_lock;
  GHashTable *fragments;
  GHashTable *urls;
  gchar *search_dir;
  gchar *fragments_dir;
  gchar *html_dir;
  GList *token_contexts;
} IndexContext;

typedef struct
{
  gchar *language;
  gchar *id;
} TokenContext;

typedef struct
{
  gchar *url;
  gchar *node_type;
  TokenContext *ctx;
  GList *languages;
} ContextualizedURL;

#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))

#define INITIAL_SELECTOR "//div[@id='main']"

#define SECTIONS_SELECTOR "./div[@id]"

/* With trie_lock */
#define add_word(t, word) trie_add_word (t, word, strlen (word), 1)

static xmlNodePtr
get_root (htmlDocPtr doc)
{
  xmlNodePtr ret = NULL;
  xmlXPathContextPtr xpathCtx = NULL;
  xmlXPathObjectPtr xpathObj = NULL;
  xmlChar *id = NULL;

  if (!(ret = xmlDocGetRootElement (doc)))
    goto done;

  if ((id = xmlGetProp (ret, (xmlChar *) "id")))
    goto done;

  xpathCtx = xmlXPathNewContext (doc);
  g_assert (xpathCtx);

  xpathObj = xmlXPathEvalExpression ((xmlChar *) INITIAL_SELECTOR, xpathCtx);
  g_assert (xpathObj);

  if (!xpathObj->nodesetval || xpathObj->nodesetval->nodeNr == 0) {
    ret = NULL;
    goto done;
  }

  ret = xpathObj->nodesetval->nodeTab[0];

done:
  if (xpathObj)
    xmlXPathFreeObject (xpathObj);
  if (xpathCtx)
    xmlXPathFreeContext (xpathCtx);
  if (id)
    xmlFree (id);

  return ret;
}

/* https://github.com/mr21/strsplit.c , MIT */
static gchar **
strsplit (const gchar *s, const gchar *del)
{
  void *data;
  gchar *_s = (gchar *) s;
  const gchar **ptrs;
  guint ptrsSize;
  guint sLen = strlen (s);
  guint delLen = strlen (del);
  guint nbWords = 1;

  while ((_s = strstr (_s, del))) {
    _s += delLen;
    ++nbWords;
  }

  ptrsSize = (nbWords + 1) * sizeof (gchar *);
  ptrs = data = g_malloc0 (ptrsSize + sLen + 1);
  if (data) {
    *ptrs = _s = strcpy (((gchar *) data) + ptrsSize, s);
    if (nbWords > 1) {
      while ((_s = strstr (_s, del))) {
        *_s = '\0';
        _s += delLen;
        *++ptrs = _s;
      }
    }
    *++ptrs = NULL;
  }

  return data;
}

static gboolean
strv_contains (const gchar * const *strv,
               const gchar *str)
{
  for (; *strv != NULL; strv++)
  {
    if (g_str_equal (str, *strv))
      return TRUE;
  }
  return FALSE;
}

static void
get_context (xmlNodePtr elem, TokenContext * ctx)
{
  if (!g_strcmp0 (ctx->language, "default")) {
    xmlChar *klasses = xmlGetProp (elem, (const xmlChar *) "class");

    if (klasses) {
      gchar **split = strsplit ((const gchar *) klasses, " ");

      if (strv_contains ((const gchar **) split, "gi-symbol") && split[1]) {
        g_free (ctx->language);
        ctx->language = g_strdup (split[1] + 10);
      }

      g_free (split);
      xmlFree (klasses);
    }
  }

  ctx->id = (gchar *) xmlGetProp (elem, (xmlChar *) "id");

  if (!ctx->id) {
    g_assert (elem->parent);
    get_context (elem->parent, ctx);
  }
}

static void
free_token_context (TokenContext *ctx)
{
  g_free (ctx->id);
  g_free (ctx->language);
  g_free (ctx);
}

/* Takes url_lock */
static void
append_url (IndexContext *idx_ctx, GHashTable *urls, const gchar *key, const gchar *url, TokenContext *ctx, const xmlChar *node_type)
{
  GList *list;
  ContextualizedURL *ctx_url;

  ctx_url = g_malloc0 (sizeof (ContextualizedURL));
  ctx_url->url = strdup (url);
  ctx_url->ctx = ctx;
  ctx_url->languages = g_list_append (NULL, g_strdup (ctx->language));
  ctx_url->node_type = g_strdup ((const gchar *) node_type);

  g_mutex_lock (&idx_ctx->url_lock);
  list = g_hash_table_lookup (urls, key);
  list = g_list_prepend (list, ctx_url);
  g_hash_table_insert (urls, strdup (key), list);
  g_mutex_unlock (&idx_ctx->url_lock);
}

static void
parse_tokens (IndexContext *idx_ctx, TokenContext *ctx, const gchar *url, gchar *str, const xmlChar *node_type)
{
  guint i = 0;

  while (!((*str >= 'a' && *str <= 'z') ||
          (*str >= 'A' && *str <= 'Z') || *str == '_')) {
    if (*str == '\0')
      return;
    str++;
  }

  while (str[i] &&
      ((str[i] >= 'a' && str[i] <= 'z') ||
          (str[i] >= 'A' && str[i] <= 'Z') ||
          (str[i] >= '0' && str[i] <= '9') || str[i] == '_' || str[i] == '.')) {
    i++;
  }

  if (i) {
    gchar *lower;
    char saved = str[i];
    guint j;

    str[i] = '\0';

    if (str[i - 1] == '.')
      str[i - 1] = '\0';

    lower = strdup (str);
    for (j = 0; lower[j]; j++)
      lower[j] = tolower (lower[j]);

    if (!g_hash_table_contains (idx_ctx->stop_words, lower)) {
      gboolean has_upper = g_strcmp0 (lower, str);

      g_mutex_lock (&idx_ctx->trie_lock);
      add_word (idx_ctx->trie, str);
      if (has_upper)
        add_word (idx_ctx->trie, lower);
      g_mutex_unlock (&idx_ctx->trie_lock);

      append_url (idx_ctx, idx_ctx->urls, str, url, ctx, node_type);
      if (has_upper)
        append_url (idx_ctx, idx_ctx->urls, lower, url, ctx, node_type);
    }

    g_free (lower);
    str[i] = saved;
  }

  /* Tail recursion, should never blow the stack */
  if (str[i] != '\0')
    parse_tokens (idx_ctx, ctx, url, str + i, node_type);
}

/* With fragment_lock */
static void
append_fragment (GHashTable *fragments, const gchar *key, const gchar *value)
{
  GList *list = g_hash_table_lookup (fragments, key);

  list = g_list_prepend (list, g_strdup (value));
  g_hash_table_insert (fragments, strdup (key), list);
}

static void
parse_content (IndexContext *idx_ctx, const gchar *filename, xmlDocPtr doc, xmlNodePtr section, xmlXPathContextPtr xpathCtx,
    xmlChar * selector)
{
  xmlXPathObjectPtr xpathObj = NULL;
  gint i;

  xpathCtx->node = section;

  xpathObj = xmlXPathEvalExpression (selector, xpathCtx);
  g_assert (xpathObj);

  if (!xpathObj->nodesetval || xpathObj->nodesetval->nodeNr == 0)
    goto done;

  for (i = 0; i < xpathObj->nodesetval->nodeNr; i++) {
    xmlChar *content = NULL;
    TokenContext *ctx;
    guint url_len;
    gchar *url;

    ctx = g_malloc0 (sizeof (TokenContext));
    idx_ctx->token_contexts = g_list_prepend (idx_ctx->token_contexts, ctx);

    ctx->language = g_strdup ("default");
    get_context (xpathObj->nodesetval->nodeTab[i], ctx);

    content = xmlNodeGetContent (xpathObj->nodesetval->nodeTab[i]);

    url_len = strlen (filename) + strlen (ctx->id) + 1 + 1;

    url = g_malloc0 (url_len * sizeof (char));

    snprintf(url, url_len, "%s#%s", filename, ctx->id);

    g_mutex_lock (&idx_ctx->fragment_lock);
    append_fragment (idx_ctx->fragments, url, (gchar *) content);
    append_fragment (idx_ctx->fragments, url, "\n");
    g_mutex_unlock (&idx_ctx->fragment_lock);

    parse_tokens (idx_ctx, ctx, url, (gchar *) content, xpathObj->nodesetval->nodeTab[i]->name);

    g_free (url);

    xmlFree (content);
  }


done:
  if (xpathObj)
    xmlXPathFreeObject (xpathObj);
}

static void
parse_sections (IndexContext *idx_ctx, const gchar *filename, xmlDocPtr doc, xmlNodePtr root)
{
  xmlXPathContextPtr xpathCtx = NULL;
  xmlXPathObjectPtr xpathObj = NULL;
  gint i;

  xpathCtx = xmlXPathNewContext (doc);
  xpathCtx->node = root;
  g_assert (xpathCtx);

  xpathObj = xmlXPathEvalExpression ((xmlChar *) SECTIONS_SELECTOR, xpathCtx);
  g_assert (xpathObj);

  if (!xpathObj->nodesetval || xpathObj->nodesetval->nodeNr == 0) {
    goto done;
  }

  for (i = 0; i < xpathObj->nodesetval->nodeNr; i++) {
    parse_content (idx_ctx, filename, doc, xpathObj->nodesetval->nodeTab[i], xpathCtx, (xmlChar *)
        ".//*[self::h1 or self::h2 or self::h3 or self::h4 or self::h5 or self::h6]");
    parse_content (idx_ctx, filename, doc, xpathObj->nodesetval->nodeTab[i], xpathCtx, (xmlChar *) ".//*[self::p]");
    parse_content (idx_ctx, filename, doc, xpathObj->nodesetval->nodeTab[i], xpathCtx, (xmlChar *) ".//*[self::ul]");
    parse_content (idx_ctx, filename, doc, xpathObj->nodesetval->nodeTab[i], xpathCtx, (xmlChar *) ".//*[self::table]");
  }

done:
  if (xpathObj)
    xmlXPathFreeObject (xpathObj);
  if (xpathCtx)
    xmlXPathFreeContext (xpathCtx);
}

typedef struct
{
  IndexContext *idx_ctx;
  guint index;
  guint step;
  guint n_files;
  PyObject *files;
} ThreadData;

static void
__create_index (IndexContext *idx_ctx, const gchar *filename)
{
  htmlDocPtr doc = NULL;
  xmlNodePtr root = NULL;
  gchar *path = g_build_filename (idx_ctx->html_dir, filename, NULL);

  doc =
      htmlReadFile (path, "UTF-8",
      HTML_PARSE_RECOVER | HTML_PARSE_NOERROR | HTML_PARSE_NOWARNING);

  if (doc == NULL) {
    fprintf (stderr, "Failed to parse %s\n", path);
    goto done;
  }

  if (!(root = get_root (doc)))
    goto done;

  parse_sections (idx_ctx, filename, doc, root);

done:
  g_free (path);

  if (doc)
    xmlFreeDoc (doc);
}

static void *
_create_index (ThreadData * tdata)
{
  while (tdata->index < tdata->n_files) {
    PyObject *item;
    const gchar *filename;
    PyGILState_STATE state;

    state = PyGILState_Ensure();
    item = PyList_GetItem(tdata->files, tdata->index);
    filename = PyUnicode_AsUTF8 (item);
    PyGILState_Release(state);

    __create_index (tdata->idx_ctx, filename);
    tdata->index += tdata->step;
  }

  g_free (tdata);

  return NULL;
}

static GHashTable *
gather_stop_words (gchar * path)
{
  FILE *file = fopen (path, "r");
  gchar *buffer = NULL;
  size_t n = 0;
  ssize_t read;
  GHashTable *res;

  res = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);

  while ((read = getline (&buffer, &n, file)) != -1) {
    buffer[read - 1] = '\0';
    g_hash_table_insert (res, strdup (buffer), NULL);
  }

  fclose (file);
  g_free (buffer);

  return res;
}

static gboolean
fill_fragment (gchar *key, GList *list, IndexContext *idx_ctx)
{
  GList *tmp;
  gchar *dest = NULL, *destdir = NULL;
  gchar *escaped = NULL, *s;
  JsonNode *jroot;
  JsonObject *jfragment;
  GString *text_string;
  gchar *text = NULL;
  gchar *serialized = NULL, *contents = NULL;
  FILE *f;

  escaped = g_strconcat (key, ".fragment", NULL);
  for (s = escaped; *s; s++) {
    if (*s == '#')
      *s = '-';
  }

  dest = g_build_filename (idx_ctx->fragments_dir, escaped, NULL);

  destdir = g_dirname (dest);
  if (!g_file_test (destdir, G_FILE_TEST_EXISTS))
    g_mkdir_with_parents (destdir, 0755);

  if (!g_file_test (destdir, G_FILE_TEST_IS_DIR))
    goto done;

  text_string = g_string_new(NULL);

  for (tmp = g_list_last (list); tmp; tmp = tmp->prev) {
    g_string_append (text_string, tmp->data);
  }

  text = g_string_free (text_string, FALSE); 

  jroot = json_node_new(JSON_NODE_OBJECT);
  jfragment = json_object_new();

  json_node_take_object (jroot, jfragment);
  json_object_set_string_member (jfragment, "url", key);
  json_object_set_string_member (jfragment, "fragment", text);

  serialized = json_to_string (jroot, FALSE);
  contents = g_strdup_printf ("fragment_downloaded_cb(%s);", serialized);
  g_free (serialized);

  json_node_unref (jroot);

  f = fopen (dest, "w");
  if (!f) {
    g_printerr ("Could not open %s\n", dest);
  } else {
    fwrite (contents, sizeof (gchar), strlen(contents), f);
    fclose(f);
  }

  g_list_free_full (list, g_free);

done:
  g_free (text);
  g_free (contents);
  g_free (destdir);
  g_free (dest);
  g_free (escaped);

  return TRUE;
}

static gpointer
save_fragment (ThreadData *tdata)
{
  gboolean done = FALSE;

  while (!done) {
    g_mutex_lock (&tdata->idx_ctx->fragment_lock);
    GHashTableIter iter;

    gpointer key, value;

    g_hash_table_iter_init (&iter, tdata->idx_ctx->fragments);
    if (g_hash_table_iter_next (&iter, &key, &value)) {
      g_hash_table_iter_steal (&iter);
      g_mutex_unlock (&tdata->idx_ctx->fragment_lock);
      fill_fragment (key, value, tdata->idx_ctx);
      g_free (key);
    } else {
      done = TRUE;
      g_mutex_unlock (&tdata->idx_ctx->fragment_lock);
    }
  }

  g_free (tdata);

  return NULL;
}

static void
fill_url_list (ContextualizedURL *ctx_url, GHashTable *deduped)
{
    ContextualizedURL *deduped_ctx_url;

    deduped_ctx_url = g_hash_table_lookup (deduped, ctx_url->url);

    if (deduped_ctx_url) {
        if (!g_list_find_custom (deduped_ctx_url->languages, ctx_url->languages->data, (GCompareFunc) g_strcmp0)) {
            deduped_ctx_url->languages = g_list_append (deduped_ctx_url->languages, g_strdup (ctx_url->languages->data));
        }
        g_free (ctx_url->url);
        ctx_url->url = NULL;
    } else {
        g_hash_table_insert (deduped, ctx_url->url, ctx_url);
    }
}

static void
show_language (gchar *lang, JsonArray *jlangs)
{
    json_array_add_string_element (jlangs, lang);
}

static void
show_url (ContextualizedURL *ctx_url, JsonArray *jurls)
{
  JsonObject *jurl;
  JsonObject *jcontext;
  JsonArray *jlangs;

  if (!ctx_url->url)
      return;

  jurl = json_object_new();
  json_object_set_string_member (jurl, "url", ctx_url->url);
  json_array_add_object_element (jurls, jurl);

  json_object_set_string_member (jurl, "node_type", ctx_url->node_type);

  jcontext = json_object_new();
  json_object_set_object_member (jurl, "context", jcontext);

  jlangs = json_array_new();
  json_object_set_array_member (jcontext, "gi-language", jlangs);

  ctx_url->languages = g_list_sort (ctx_url->languages, (GCompareFunc) g_strcmp0);

  g_list_foreach (ctx_url->languages, (GFunc) show_language, jlangs);
}

static gint
sort_url (ContextualizedURL *url1, ContextualizedURL *url2)
{
  return g_strcmp0 (url1->url, url2->url);
}

static void
free_contextualized_url (ContextualizedURL *url)
{
  g_free (url->url);
  g_list_free_full (url->languages, g_free);
  g_free (url->node_type);
  g_free (url);
}

static gboolean
fill_url (gchar *key, GList *list, IndexContext *ctx)
{
  GHashTable *deduped;
  JsonNode *jroot = json_node_new (JSON_NODE_OBJECT);
  JsonObject *jtoken = json_object_new();
  JsonArray *jurls = json_array_new();
  gchar *serialized;
  gchar *filename;
  gchar *contents;
  FILE *f;

  deduped = g_hash_table_new (g_str_hash, g_str_equal);

  list = g_list_sort (list, (GCompareFunc) sort_url);

  g_list_foreach (list, (GFunc) fill_url_list, deduped);

  json_node_take_object (jroot, jtoken);
  json_object_set_string_member (jtoken, "token", key);
  json_object_set_array_member (jtoken, "urls", jurls);

  g_list_foreach (list, (GFunc) show_url, jurls);

  serialized = json_to_string (jroot, FALSE);
  contents = g_strdup_printf ("urls_downloaded_cb(%s);", serialized);
  g_free (serialized);

  filename = g_build_filename (ctx->search_dir, key, NULL);

  f = fopen (filename, "w");
  fwrite (contents, sizeof (gchar), strlen(contents), f);
  fclose(f);

  g_free (contents);
  g_free (filename);

  json_node_unref (jroot);
  g_hash_table_unref (deduped);

  g_list_free_full (list, (GDestroyNotify) free_contextualized_url);

  return TRUE;
}

static gpointer
save_url (ThreadData *tdata)
{
  gboolean done = FALSE;

  while (!done) {
    g_mutex_lock (&tdata->idx_ctx->url_lock);
    GHashTableIter iter;

    gpointer key, value;

    g_hash_table_iter_init (&iter, tdata->idx_ctx->urls);
    if (g_hash_table_iter_next (&iter, &key, &value)) {
      g_hash_table_iter_steal (&iter);
      g_mutex_unlock (&tdata->idx_ctx->url_lock);
      fill_url (key, value, tdata->idx_ctx);
      g_free (key);
    } else {
      done = TRUE;
      g_mutex_unlock (&tdata->idx_ctx->url_lock);
    }
  }

  g_free (tdata);

  return NULL;
}

static PyObject *
create_index (PyObject * self, PyObject * args)
{
  PyObject *files;
  guint n_threads;
  guint i;
  GThread **threads;
  Py_ssize_t n_files;
  IndexContext ctx;
  PyThreadState* mainPyThread;
  gchar *private_dir;
  gchar *trie_path, *trie_js_path;
  gchar *stopwords_path;

  if (!PyArg_ParseTuple(args, "OIsssss", &files, &n_threads, &ctx.search_dir, &ctx.fragments_dir, &ctx.html_dir, &private_dir, &stopwords_path))
    return NULL;

  mainPyThread = PyEval_SaveThread();

  ctx.stop_words = gather_stop_words (stopwords_path);
  ctx.trie = trie_new();
  ctx.fragments = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);
  ctx.urls = g_hash_table_new_full (g_str_hash, g_str_equal, g_free, NULL);
  ctx.token_contexts = NULL;
  g_mutex_init (&ctx.url_lock);
  g_mutex_init (&ctx.fragment_lock);
  g_mutex_init (&ctx.trie_lock);

  n_files = PyList_Size (files);

  n_threads = n_threads < n_files ? n_threads : n_files;

  threads = g_malloc0(sizeof (GThread *) * n_threads);

  for (i = 0; i < n_threads; i++) {
    ThreadData *tdata = g_malloc0(sizeof(ThreadData));

    tdata->index = i;
    tdata->step = n_threads;
    tdata->files = files;
    tdata->n_files = n_files;
    tdata->idx_ctx = &ctx;

    threads[i] = g_thread_new (NULL, (GThreadFunc) _create_index, tdata);
  }
  for (i = 0; i < n_threads; i++)
    g_thread_join (threads[i]);

  for (i = 0; i < n_threads; i++) {
    ThreadData *tdata = g_malloc0(sizeof(ThreadData));
    tdata->idx_ctx = &ctx;
    threads[i] = g_thread_new (NULL, (GThreadFunc) save_fragment, tdata);
  }

  for (i = 0; i < n_threads; i++)
    g_thread_join (threads[i]);

  for (i = 0; i < n_threads; i++) {
    ThreadData *tdata = g_malloc0(sizeof(ThreadData));
    tdata->idx_ctx = &ctx;
    threads[i] = g_thread_new (NULL, (GThreadFunc) save_url, tdata);
  }

  for (i = 0; i < n_threads; i++)
    g_thread_join (threads[i]);

  trie_path = g_build_filename(ctx.html_dir, "dumped.trie", NULL);
  trie_js_path = g_build_filename(ctx.html_dir, "assets", "js", "trie_index.js", NULL);

  trie_encode (ctx.trie, trie_path, trie_js_path);

  g_free (trie_path);
  g_free (trie_js_path);

  g_mutex_clear (&ctx.url_lock);
  g_mutex_clear (&ctx.fragment_lock);
  g_mutex_clear (&ctx.trie_lock);
  g_hash_table_unref (ctx.stop_words);
  g_hash_table_unref (ctx.fragments);
  g_hash_table_unref (ctx.urls);
  g_list_free_full (ctx.token_contexts, (GDestroyNotify) free_token_context);
  trie_free (ctx.trie);
  g_free (threads);

  PyEval_RestoreThread(mainPyThread);

  Py_INCREF (Py_None);
  return Py_None;
}

static PyMethodDef search_methods[] = {
  {"create_index", create_index, METH_VARARGS,
      "Create search index from a list of source files"},
  {NULL, NULL, 0, NULL}
};

static int
search_traverse (PyObject * m, visitproc visit, void *arg)
{
  Py_VISIT (GETSTATE (m)->error);
  return 0;
}

static int
search_clear (PyObject * m)
{
  Py_CLEAR (GETSTATE (m)->error);
  return 0;
}

static struct PyModuleDef moduledef = {
  PyModuleDef_HEAD_INIT,
  "search",
  NULL,
  sizeof (struct module_state),
  search_methods,
  NULL,
  search_traverse,
  search_clear,
  NULL
};

PyMODINIT_FUNC
PyInit_search (void)
{
  PyObject *module = PyModule_Create (&moduledef);

  if (module == NULL)
    return NULL;

  return module;
}
