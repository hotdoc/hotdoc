%{
 
/*
 * Lexer.l file
 * To generate the lexical analyzer run: "flex Lexer.l"
 */

#include "parser.h" 
#include <stdio.h>

#define YY_USER_ACTION yylloc->first_line = yylloc->last_line = yylineno;

extern yyscan_t my_scanner;
static int parameters_done = 0;

%}

%option header-file="better_doc_tool/lexer_parsers/gtkdoc_parser/lexer.h"
%option warn nodefault
%option nounput
%option noinput
%option reentrant noyywrap never-interactive nounistd
%option bison-bridge
%option bison-locations
%option yylineno
%option stack
%option debug

/* Generic */
WS                  [ \t\r\n]
SLASH               \/
STAR                \*
BLANK               [ \t\r]
NEWLINE             \n{BLANK}*{STAR}
EMPTYLINE           {NEWLINE}{BLANK}*
NEWPARA             {EMPTYLINE}{EMPTYLINE}+

/* inherited from doxygen lexer */
ID                  "$"?[a-z_A-Z\x80-\xFF][a-z_A-Z0-9\x80-\xFF]*
CHARWORDQ           [^ \t\n\r\\@<>()\[\]:;\?{}&%$#,."=']
WORD1               {ID}|{CHARWORDQ}+|"{"|"}"|"'\"'"|("\""[^"\n]*\n?[^"\n]*"\"")
WORD2               "."|","|"("|")"|"["|"]"|":"|";"|"\?"|"="|"'"
WORD                {WORD1}|{WORD2}

/* Initial state */
CCOMMENT_START      {SLASH}{STAR}{STAR}
CCOMMENT_END        ({WS}*{STAR}{SLASH})|{EMPTYLINE}+{NEWLINE}{SLASH}

/* Annotations */
ANN_START           {BLANK}*\({BLANK}*
ANN_END             {BLANK}*\)

ANN_ARG_VALUE       {BLANK}*={BLANK}*{WORD}{BLANK}*

ANN_ARG_KV          {BLANK}+{WORD}{ANN_ARG_VALUE}

ANN_NO_ARG          {ANN_START}{WORD}{ANN_END}{BLANK}*
ANN_1ARG            {ANN_START}{WORD}{BLANK}*{WORD}{ANN_END}{BLANK}*
ANN_KV_ARGS         {ANN_START}{WORD}{ANN_ARG_KV}*{ANN_END}

ANN                 {ANN_NO_ARG}|{ANN_1ARG}|{ANN_KV_ARGS}

WORD_NO_WS          {BLANK}*{WORD}{BLANK}*

/* Parameters */
PARAM               {NEWLINE}{BLANK}*"@"

TAG                 ("Since"|"since"|"Returns"|"returns")

/* Block */

BLOCK_NAME          {WORD1}|{WORD1}"::"{WORD1}|{WORD1}:{WORD1}
SECTION_NAME        "SECTION:"{WORD1}

/* References */

PARAM_REF           "@"

/* Code blocks */

CODE_START          "|["
CODE_START_LANG_S   "|[<!-- language=\""
CODE_START_LANG_E   "\" -->"
CODE_END            "]|"

%x St_In_Comment
%x St_In_Block_Name
%x St_In_Block
%x St_In_Tag
%x St_In_Annotatable
%x St_In_Ann_Name
%x St_In_Ann_Arg
%x St_In_Ann_Arg_Key_Value
%x St_In_Tag_Value
%x St_In_Param
%x St_In_Code

%%

<St_In_Ann_Arg_Key_Value>= {
}

<St_In_Ann_Arg_Key_Value>{WORD}/{ANN_ARG_KV} {
  yylval->text = yytext;
  return TK_ANNOTATION_ARG_VALUE;
}

<St_In_Ann_Arg_Key_Value>{WORD} {
  BEGIN (St_In_Ann_Name);
  yylval->text = yytext;
  return TK_ANNOTATION_ARG_VALUE;
}

<St_In_Ann_Arg_Key_Value>{WORD}/{ANN_ARG_VALUE} {
  yylval->text = yytext;
  return TK_ANNOTATION_ARG_KEY;
}

<St_In_Ann_Arg>{WORD}/{ANN_END} {
  BEGIN (St_In_Ann_Name);
  yylval->text = yytext;
  return TK_ANNOTATION_ARG;
}

<St_In_Ann_Name>{ANN_END}/:       {
  yy_pop_state (my_scanner);
}

<St_In_Ann_Name>{ANN_END}|{ANN_START}

<St_In_Ann_Name>{WORD}/{ANN_END} {
  yylval->text = yytext;
  return TK_ANNOTATION_NAME;
}

<St_In_Ann_Name>{WORD}/{ANN_ARG_KV} {
  BEGIN (St_In_Ann_Arg_Key_Value);
  yylval->text = yytext;
  return TK_ANNOTATION_NAME;
}


<St_In_Ann_Name>{WORD} {
  BEGIN (St_In_Ann_Arg);
  yylval->text = yytext;
  return TK_ANNOTATION_NAME;
}

<St_In_Annotatable>{NEWLINE} {
}

<St_In_Annotatable>:/{ANN}+: {
  BEGIN (St_In_Ann_Name);
}

<St_In_Annotatable>{WORD} {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Param>:      {
  BEGIN (St_In_Comment);
}

<St_In_Param>{WORD} {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Tag>{WORD}/{BLANK}*:{ANN}+: {
  yy_push_state (St_In_Annotatable, my_scanner);
  yylval->text = yytext;
  return TK_TAG;
}

<St_In_Tag>{WORD}/{BLANK}*: {
  yylval->text = yytext;
  return TK_TAG;
}

<St_In_Tag_Value>{WORD} {
  return TK_TAG_VALUE;
}

<St_In_Tag>{WORD}/{ANN}+:{WORD_NO_WS}: {
  BEGIN (St_In_Tag_Value);
  yy_push_state (St_In_Annotatable, my_scanner);
  yylval->text = yytext;
  return TK_TAG;
}

<St_In_Block>{SECTION_NAME} {
  yylval->text = yytext;
  BEGIN (St_In_Comment);
  return TK_BLOCK_NAME;
}

<St_In_Block>{BLOCK_NAME}/{BLANK}*:{ANN}+: {
  yy_push_state (St_In_Annotatable, my_scanner);
  yylval->text = yytext;
  return TK_BLOCK_NAME;
}

<St_In_Block>{BLOCK_NAME}/{BLANK}*: {
  yylval->text = yytext;
  return TK_BLOCK_NAME;
}

<St_In_Tag,St_In_Tag_Value,St_In_Block>: {
  BEGIN (St_In_Comment);
}

<St_In_Block_Name>{NEWLINE}|{EMPTYLINE}|{NEWPARA}/{BLOCK_NAME}:    {
  BEGIN (St_In_Block);
}

<*>{CCOMMENT_END}                    {
  parameters_done = 0;
  if (YY_START == St_In_Code) {
    yylval->text = yytext;   
    return TK_WORD;
  }
  if (YY_START != INITIAL) {
    BEGIN (INITIAL);
    return TK_COMMENT_END;
  }
}

{CCOMMENT_START}/\n         {
  yylineno -= 1;
  BEGIN (St_In_Block_Name);
  return TK_COMMENT_START;
}

<St_In_Comment>{PARAM}/{WORD}{BLANK}*:{ANN}+: {
  BEGIN (St_In_Param);
  yy_push_state (St_In_Annotatable, my_scanner);
  return TK_PARAM;
}

<St_In_Comment>{PARAM} {
  if (!parameters_done) {
    BEGIN (St_In_Param);
    return TK_PARAM;
  }

  return TK_PARAM_REF;
}

<St_In_Comment>{PARAM_REF}/{WORD} {
  return TK_PARAM_REF;
}

<St_In_Comment>%/{ID} {
  return TK_TYPE_REF;
}

<St_In_Comment>{ID}/\(\)            {
  yylval->text = yytext;
  return TK_FUNCTION_REF;
}

<St_In_Comment>{BLOCK_NAME}         {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Comment>#/{BLOCK_NAME} {
  return TK_TYPE_REF; 
}

<St_In_Comment>{NEWLINE}|{NEWPARA}/{TAG}:    {
  BEGIN (St_In_Tag);
}

<St_In_Comment>{WORD}    {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Comment>{CODE_START} {
  BEGIN (St_In_Code);
  return TK_CODE_START;
}

<St_In_Code>{NEWLINE} {
  yylval->text = "\n";
  return TK_WORD;
}

<St_In_Code>. {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Code>{CODE_END}   {
  BEGIN (St_In_Comment);
  return TK_CODE_END;
}

<St_In_Comment>{NEWPARA}  {
  parameters_done = 1;
  yylval->text = yytext;
  return TK_NEWPARA;
}

<St_In_Comment>{NEWLINE} {
  return TK_NEWLINE;
}

<St_In_Comment>{BLANK} {
  yylval->text = yytext;
  return TK_WS;
}

<*>. {
}

<*>\n {
}

%%
