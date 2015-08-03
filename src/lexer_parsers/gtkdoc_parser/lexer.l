%{
 
/*
 * Lexer.l file
 * To generate the lexical analyzer run: "flex Lexer.l"
 */

#include "parser.h" 
#include <stdio.h>

extern yyscan_t my_scanner;

%}

%option header-file="gtkdoc_parser/lexer.h"
%option warn nodefault
%option nounput
%option noinput
%option reentrant noyywrap never-interactive nounistd
%option bison-bridge
%option yylineno
%option stack

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
ESCWORD             ("%"{ID}(("::"|"."){ID})*)|("%'")
WORD1               {ESCWORD}|{CHARWORDQ}+|"{"|"}"|"'\"'"|("\""[^"\n]*\n?[^"\n]*"\"")
WORD2               "."|","|"("|")"|"["|"]"|":"|";"|"\?"|"="|"'"
WORD                {WORD1}|{WORD2}

/* Initial state */
CCOMMENT_START      {SLASH}{STAR}{STAR}
CCOMMENT_END        {WS}*{STAR}{SLASH}

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

%x St_In_Comment
%x St_In_Block_Name
%x St_In_Block
%x St_In_Tag
%x St_In_Annotatable
%x St_In_Ann_Name
%x St_In_Ann_Arg
%x St_In_Ann_Arg_Key_Value
%x St_In_Tag_Value

%%

<St_In_Ann_Arg_Key_Value>= {
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

<St_In_Ann_Name>{ANN_START}     {
}

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

<St_In_Comment>{PARAM}/{BLANK}*:{ANN}+: {
  yy_push_state (St_In_Annotatable, my_scanner);
  return TK_PARAM;
}

<St_In_Comment>{PARAM} {
  return TK_PARAM;
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
  if (YY_START != INITIAL) {
    BEGIN (INITIAL);
    return TK_COMMENT_END;
  }
}

{CCOMMENT_START}/\n         {
  BEGIN (St_In_Block_Name);
  return TK_COMMENT_START;
}

<St_In_Comment>{NEWLINE}|{NEWPARA}/{TAG}:    {
  BEGIN (St_In_Tag);
}

<St_In_Comment>{WORD}    {
  yylval->text = yytext;
  return TK_WORD;
}

<St_In_Comment>{NEWPARA}  {
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
