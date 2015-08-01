#include <Python.h>
#include <stdio.h>
#include <stdlib.h>
#include <glib.h>
#include "doxparser.h"
#include "doxenizer.h"
  
extern int yylex (void);
static PyObject *comment_block_class;
static PyObject *add_param_block_pyname;
static PyObject *set_return_block_pyname;
static PyObject *set_description_pyname;

typedef void (*DoxParsingFunction)(DoxParser *);

static void parse_para (DoxParser *self, PyObject *block);


static void
parse_param_or_return_value (DoxParser *self, gboolean is_return)
{
  int tok;
  PyObject *param_block;
  GString *param_name;
  PyObject *pyparam_name = NULL;
  PyObject *res;
  doctokenizerYYsetStateParam();

  tok = yylex();
  if (tok == 0) {
    printf ("Premature end of param block\n");
    return;
  }

  if (!is_return) {
    param_name = g_string_new (NULL);

    while (tok==TK_WORD) /* there is a parameter name */
    {
      g_string_append (param_name, g_token->name->str);
      tok = yylex();
    }
    pyparam_name = PyString_FromString (param_name->str);
    g_string_free (param_name, TRUE);

    if (tok != TK_WHITESPACE) {
      printf ("unexpected token in comment block while parsing the "
          "argument of param command\n");
      printf ("token type : %s, token : %s\n", tokToString (tok), g_token->name->str);
      Py_DECREF (pyparam_name);
      return;
    }
  }

  param_block = PyObject_CallObject(comment_block_class, NULL);

  if (!is_return) {
    res = PyObject_CallMethodObjArgs (self->current_block,
        add_param_block_pyname, pyparam_name, param_block, NULL);
    Py_DECREF (pyparam_name);
  } else {
    res = PyObject_CallMethodObjArgs (self->current_block,
        set_return_block_pyname, param_block, NULL);
  }

  Py_DECREF (res);
  Py_DECREF (param_block);

  parse_para (self, param_block);
}

static void parse_param (DoxParser *self) {
  parse_param_or_return_value (self, FALSE);
}

static void parse_return_value (DoxParser *self) {
  parse_param_or_return_value (self, TRUE);
}

static void
parse_command (DoxParser *self)
{
  int tok = yylex();
  DoxParsingFunction cmd_func;

  if (tok != TK_WHITESPACE) {
    printf ("Expected whitespace after %s command", g_token->name->str);
    return;
  }

  cmd_func = (DoxParsingFunction) (g_hash_table_lookup (self->command_map, g_token->name->str));

  if (!cmd_func) {
    printf ("Unhandled command [%s]\n", g_token->name->str);
    return;
  }

  cmd_func (self);
}

static void
parse_para (DoxParser *self, PyObject *block)
{
  int tok;
  GString *contents = g_string_new(NULL);
  PyObject *description;
  PyObject *res;

  doctokenizerYYsetStatePara ();
  while ((tok = yylex ())) {
    switch(tok)
    {
      case TK_WORD:
        g_string_append (contents, g_token->name->str);
        break;
      case TK_WHITESPACE:
        {
          g_string_append (contents, g_token->chars);
        }
        break;
      case TK_COMMAND: 
        {
          parse_command (self);
        }
        break;
      case TK_NEWPARA:     
        goto endparagraph;
      default:
        printf ("found unexpected token, %s %s", tokToString (tok), g_token->name->str);
        break;	
    }
  }

endparagraph:
  description = PyString_FromString (contents->str);
  res = PyObject_CallMethodObjArgs (block,
      set_description_pyname, description, NULL);
  Py_DECREF (res);
  Py_DECREF (description);
  g_string_free (contents, TRUE);
}

PyObject *dox_parser_parse (DoxParser *self, const char *raw_comment)
{
  PyObject *block = PyObject_CallObject(comment_block_class, NULL);
  int tok;

	g_token = (TokenInfo *) malloc (sizeof (TokenInfo));
  g_token->name = g_string_new (NULL);

	doctokenizerYYinit (raw_comment);
  self->current_block = block;
  while ((tok = yylex ()) != TK_NEWPARA && tok);

  if (!tok) {
    printf ("Empty block !\n");
  } else {
	  parse_para (self, block);
  }
	return block;
}

typedef struct
{
  gchar *key;
  void *value;
} Assoc;

Assoc command_assocs[]  = {
  {"param", parse_param},
  {"returns", parse_return_value},
  {NULL, NULL}
};

static GHashTable *
g_hash_table_new_from_assocs (Assoc *assocs, GDestroyNotify value_destroy_func)
{
  gint i = 0;
  GHashTable *res = g_hash_table_new_full (g_str_hash,
      g_str_equal, g_free, value_destroy_func);

  while (assocs[i].key != NULL) {
    g_hash_table_insert (res, g_strdup(assocs[i].key), assocs[i].value);
    i += 1;
  }

  return res;
}

DoxParser *
dox_parser_new (void)
{
  DoxParser *ret = (DoxParser *) g_malloc0 (sizeof (DoxParser));

  PyObject *comment_module = PyImport_ImportModule("comment_block");
  comment_block_class = PyObject_GetAttrString (comment_module, "CommentBlock");
  add_param_block_pyname = PyString_FromString ("add_param_block");
  set_description_pyname = PyString_FromString ("set_description");
  set_return_block_pyname = PyString_FromString ("set_return_block");

  ret->command_map = g_hash_table_new_from_assocs (command_assocs, (GDestroyNotify) NULL);
  return ret;
}

void
dox_parser_dispose (DoxParser *parser)
{
  g_hash_table_unref (parser->command_map);
  g_free (parser);
}
