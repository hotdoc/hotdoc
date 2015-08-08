%{

#include "parser.h"
#include "lexer.h"
#include "comment_module_interface.h"

static int yyerror(YYLTYPE * location, yyscan_t scanner, PyObject **block, const char *msg) {
	fprintf(stderr,"Error at line %d :%s\n", location->first_line, msg);
	return 0;
}

extern yyscan_t my_scanner;

%}

%code requires {

#ifdef _POSIX_C_SOURCE
  #undef _POSIX_C_SOURCE
#endif

#ifdef _XOPEN_SOURCE
  #undef _XOPEN_SOURCE
#endif

#include <Python.h>

#ifndef YY_TYPEDEF_YY_SCANNER_T
#define YY_TYPEDEF_YY_SCANNER_T
typedef void* yyscan_t;
#endif

}

%output  "gtkdoc_parser/parser.c"
%defines "gtkdoc_parser/parser.h"

%locations
%error-verbose

%define api.pure
%lex-param   { yyscan_t scanner }
%parse-param { yyscan_t scanner }
%parse-param { PyObject **blocks }

%union {
	char *text;
	PyObject *py_object;
}

%token TK_PARAM
%token TK_COMMENT_START
%token TK_COMMENT_END
%token TK_PARAM_REF
%token TK_TYPE_REF
%token TK_CODE_START
%token TK_CODE_END
 
%token <text> TK_WORD
%token <text> TK_WS
%token <text> TK_NEWLINE
%token <text> TK_NEWPARA
%token <text> TK_TAG
%token <text> TK_BLOCK_NAME
%token <text> TK_TAG_VALUE
%token <text> TK_ANNOTATION_NAME
%token <text> TK_ANNOTATION_ARG
%token <text> TK_ANNOTATION_ARG_KEY
%token <text> TK_ANNOTATION_ARG_VALUE
%token <text> TK_FUNCTION_REF

%type <py_object> block
%type <text> identifier
%type <text> tag_value
%type <text> tag_name
%type <text> block_name
%type <text> word
%type <text> annotation_name
%type <text> annotation_arg

%type <py_object> extension
%type <py_object> paragraph
%type <py_object> paragraphs
%type <py_object> parameter;
%type <py_object> parameters;
%type <py_object> annotations;
%type <py_object> annotation_1arg;
%type <py_object> simple_annotation;
%type <py_object> key_value_annotation;
%type <py_object> annotation;
%type <py_object> tags;
%type <py_object> tag;
%type <py_object> key;
%type <py_object> value;
%type <py_object> key_values;
%type <py_object> input;
%type <py_object> block_description

%%
 
input
	:
{
	*blocks = PyList_New(0);
	$$ = *blocks;
}
	| input block
{
	if ($2)
		PyList_Append($$, $2);
}
;

word
	: TK_WORD
	| TK_WS
{ $$ = $1; }
;

extension
	: TK_PARAM_REF TK_WORD { $$ = PyString_FromFormat ("*%s*", $2); }
	| TK_FUNCTION_REF { $$ = PyString_FromFormat ("[%s]", $1); }
	| TK_TYPE_REF TK_WORD { $$ = PyString_FromFormat ("[%s]()", $2); }
	| TK_TYPE_REF TK_FUNCTION_REF
{
	$$ = PyString_FromFormat ("[%s]", $2);
	//printf ("Warning, trying to reference to a function with unneeded #\n");
}
	| TK_PARAM_REF TK_FUNCTION_REF
{
	$$ = PyString_FromFormat ("*%s*()", $2);
}
	| TK_CODE_START { $$ = PyString_FromString ("\n```\n"); }
	| TK_CODE_END   { $$ = PyString_FromString ("\n```\n"); }
;

paragraph
	: { $$ = PyString_FromString (""); }
	| paragraph word
{
	PyString_ConcatAndDel (&$$, PyString_FromString ($2));
}
	| paragraph TK_NEWLINE
{
	PyString_ConcatAndDel (&$$, PyString_FromString ("\n"));
}
	| paragraph extension
{
	PyString_ConcatAndDel (&$$, $2);
}
;

paragraphs
	: { $$ = PyString_FromString (""); }
	| paragraphs word
{
	PyString_ConcatAndDel (&$$, PyString_FromString ($2));
}
	| paragraphs TK_NEWLINE
{
	PyString_ConcatAndDel (&$$, PyString_FromString ("\n"));
}
	| paragraphs TK_NEWPARA
{
	PyString_ConcatAndDel (&$$, PyString_FromString ("\n\n"));
}
	| paragraphs extension
{
	PyString_ConcatAndDel (&$$, $2);
}
;

identifier
	: TK_WORD { $$ = strdup ($1); }

annotation_name
	: TK_ANNOTATION_NAME
{
	$$ = strdup ($1);
}
;

annotation_arg
	: TK_ANNOTATION_ARG
{
	$$ = strdup ($1);
}
;

annotation_1arg
	: annotation_name annotation_arg
{
	PyObject *list = PyList_New(0);
	PyList_Append (list, PyString_FromString ($2));
	$$ = create_annotation ($1, list);
	free ($1);
	free ($2);
}
;

simple_annotation
	: annotation_name
{
	$$ = create_annotation ($1, PyList_New(0));
	free ($1);
}
;

key
	: TK_ANNOTATION_ARG_KEY
{
	$$ = PyString_FromString ($1);
}
;

value
	: TK_ANNOTATION_ARG_VALUE
{
	$$ = PyString_FromString ($1);
}
;

key_values
	: key value
{
	$$ = PyDict_New ();
	PyDict_SetItem ($$, $1, $2);
	Py_DECREF ($1);
	Py_DECREF ($2);
}
	| key_values key value
{
	PyDict_SetItem ($$, $2, $3);
	Py_DECREF ($2);
	Py_DECREF ($3);
}
;

key_value_annotation
	: annotation_name key_values
{
	$$ = create_annotation ($1, $2);
}
;

annotation
	: simple_annotation
	| annotation_1arg
	| key_value_annotation
{
	$$ = $1;
}
;

annotations
	: { $$ = PyList_New (0); }
	| annotations annotation
{
	PyList_Append ($$, $2);
	Py_DECREF ($2);
}
;

parameter
	: TK_PARAM identifier annotations paragraph
{
	$$ = create_parameter ($2, $4, $3);
	free ($2);
}
;

parameters
	:
{
	$$ = PyList_New (0);
}
	| parameters parameter
{
	PyList_Append ($$, $2);
	Py_DECREF ($2);
}
;

tag_value
	: { $$ = NULL; }
	| TK_TAG_VALUE { $$ = strdup($1); }
;


tag_name
	: TK_TAG
{
	$$ = strdup($1);
}
;

tag
	: tag_name annotations tag_value paragraphs
{
	$$ = create_tag ($1, $3, $4, $2);
	free ($1);
}
;

tags
	:
{
	$$ = PyList_New (0);
}
	| tags tag
{
	PyList_Append ($$, $2);
	Py_DECREF ($2);
}
;

block_name
	: TK_BLOCK_NAME
{
	$$ = strdup($1);
}
	| block_name TK_WORD
{
	//printf ("Skipping unrecognized token at line %d after block name : [%s]\n",
		//yyget_lineno(my_scanner), $2);
	//printf ("If that was an annotation, you need to add a colon after it.\n");
}
	| block_name TK_WS
	| block_name TK_NEWLINE
;

block_description
	: { $$ = PyString_FromString (""); }
	| TK_NEWPARA paragraphs { $$ = $2; }
;

block
	: TK_COMMENT_START block_name annotations parameters block_description tags TK_COMMENT_END
{
	PyObject *new_block;
	create_comment_block (&new_block, $2, $3, $4, $5, $6);
	free ($2);
	$$ = new_block;
}
	| error
{
	$$ = NULL;
}
;

%%
