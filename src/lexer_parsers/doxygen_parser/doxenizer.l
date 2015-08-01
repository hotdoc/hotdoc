/******************************************************************************
 *
 * $Id: $
 *
 *
 * Copyright (C) 1997-2015 by Dimitri van Heesch.
 *
 * Permission to use, copy, modify, and distribute this software and its
 * documentation under the terms of the GNU General Public License is hereby 
 * granted. No representations are made about the suitability of this software 
 * for any purpose. It is provided "as is" without express or implied warranty.
 * See the GNU General Public License for more details.
 *
 * Documents produced by Doxygen are derivative works derived from the
 * input used in their production; they are not affected by this license.
 *
 */

%option never-interactive
%{

#include <ctype.h>

#include "doxenizer.h"

#define YY_NO_INPUT 1
#define YY_NO_UNISTD_H 1
  
//--------------------------------------------------------------------------

struct _Definition
{
	char *filebase;
};

struct _MemberGroup
{
	Definition *parent;
};

typedef struct
{
} SectionInfo;

// context for tokenizer phase
TokenInfo *g_token = 0;
static int g_inputPos = 0;
static const char *g_inputString;

// context for section finding phase

struct DocLexerContext
{
  TokenInfo *token;
  int rule;
  int autoListLevel;
  int inputPos;
  const char *inputString;
  YY_BUFFER_STATE state;
};

#define SET_TOKEN_NAME(new_name)           \
G_STMT_START {                         \
  g_string_free (g_token->name, TRUE); \
  g_token->name = g_string_new (new_name); \
} G_STMT_END                           \
                    

/* static QStack<DocLexerContext> g_lexerStack; */

//--------------------------------------------------------------------------

/*
void doctokenizerYYpushContext()
{
  DocLexerContext *ctx = new DocLexerContext;
  ctx->rule = YY_START;
  ctx->autoListLevel = g_autoListLevel;
  ctx->token = g_token;
  ctx->inputPos = g_inputPos;
  ctx->inputString = g_inputString;
  ctx->state = YY_CURRENT_BUFFER;
  g_lexerStack.push(ctx);
  yy_switch_to_buffer(yy_create_buffer(doctokenizerYYin, YY_BUF_SIZE));
}

bool doctokenizerYYpopContext()
{
  if (g_lexerStack.isEmpty()) return false;
  DocLexerContext *ctx = g_lexerStack.pop();
  g_autoListLevel = ctx->autoListLevel;
  g_inputPos = ctx->inputPos;
  g_inputString = ctx->inputString;
  yy_delete_buffer(YY_CURRENT_BUFFER);
  yy_switch_to_buffer(ctx->state);
  BEGIN(ctx->rule);
  delete ctx;
  return true;
}
*/

//--------------------------------------------------------------------------

const char *tokToString(int token)
{
  switch (token)
  {
    case 0:              return "TK_EOF";
    case TK_WORD:        return "TK_WORD";
    case TK_WHITESPACE:  return "TK_WHITESPACE";
    case TK_COMMAND:     return "TK_COMMAND";
    case TK_NEWPARA:     return "TK_NEWPARA";
  }
  return "ERROR";
}

static int computeIndent(const char *str,int length)
{
  int i;
  int indent=0;
  static int tabSize=4;
  for (i=0;i<length;i++)
  {
    if (str[i]=='\t')
    {
      indent+=tabSize - (indent%tabSize);
    }
    else if (str[i]=='\n')
    {
      indent=0;
    }
    else
    {
      indent++;
    }
  }
  return indent;
}

//--------------------------------------------------------------------------

#undef  YY_INPUT
#define YY_INPUT(buf,result,max_size) result=yyread(buf,max_size);

static int yyread(char *buf,int max_size)
{
  int c=0;
  const char *src=g_inputString+g_inputPos;
  while ( c < max_size && *src ) *buf++ = *src++, c++;
  g_inputPos+=c;
  return c;
}

//--------------------------------------------------------------------------
extern int yylex (void);
#define YY_DECL int yylex (void)

%}

CMD             ("\\"|"@")
WS              [ \t\r\n]
SLASH           \/
STAR            \*
BLANK           [ \t\r]
CCOMMENT_START  {SLASH}{STAR}*
CCOMMENT_END    {WS}*{STAR}{SLASH}
LONE_STAR       \n{BLANK}*{STAR}
ID              "$"?[a-z_A-Z\x80-\xFF][a-z_A-Z0-9\x80-\xFF]*
LABELID         [a-z_A-Z\x80-\xFF][a-z_A-Z0-9\x80-\xFF\-]*
PHPTYPE         [\\:a-z_A-Z0-9\x80-\xFF\-]+
VERBATIM        "verbatim"{BLANK}*
SPCMD1          {CMD}([a-z_A-Z][a-z_A-Z0-9]*|{VERBATIM}|"--"|"---")
SPCMD2          {CMD}[\\@<>&$#%~".|]
SPCMD4          {CMD}"::"
INOUT	          "inout"|"in"|"out"|("in"{BLANK}*","{BLANK}*"out")|("out"{BLANK}*","{BLANK}*"in")
PARAMIO         {CMD}param{BLANK}*"["{BLANK}*{INOUT}{BLANK}*"]"
CHARWORDQ       [^ \t\n\r\\@<>()\[\]:;\?{}&%$#,."=']
ESCWORD         ("%"{ID}(("::"|"."){ID})*)|("%'")
WORD1           {ESCWORD}|{CHARWORDQ}+|"{"|"}"|"'\"'"|("\""[^"\n]*\n?[^"\n]*"\"")
WORD2           "."|","|"("|")"|"["|"]"|":"|";"|"\?"|"="|"'"

%option noyywrap
%option yylineno

%x St_Para
%x St_Param
%s St_Initial

%%

<*>{CCOMMENT_END}                    {
  BEGIN (St_Initial); /* Shouldn't really matter but whatev */
}

<*>{LONE_STAR}                       {
}

<St_Initial>{CCOMMENT_START}         {
  BEGIN (St_Para);
  return TK_NEWPARA;
}

<St_Para>\r            /* skip carriage return */
<St_Para>"{"{BLANK}*"@link" {
  SET_TOKEN_NAME("javalink");
  return TK_COMMAND;
}

<St_Para>"{"{BLANK}*"@inheritDoc"{BLANK}*"}" {
  SET_TOKEN_NAME("inheritdoc");
  return TK_COMMAND;
}

<St_Para>{CMD}"n"\n    { /* \n followed by real newline */
  yylineno++;
  SET_TOKEN_NAME (g_strstrip (yytext+1));
  g_token->paramDir=Unspecified;
  return TK_COMMAND;
}

<St_Para>{SPCMD1}      |
<St_Para>{SPCMD2}      |
<St_Para>{SPCMD4}      { /* special command */
  SET_TOKEN_NAME (g_strstrip (yytext+1));
  g_token->paramDir=Unspecified;
  return TK_COMMAND;
}

<St_Para>{PARAMIO}     { /* param [in,out] command */
  SET_TOKEN_NAME ("param");
  char *s = yytext;
  bool isIn  = strstr(s, "in") != NULL;
  bool isOut = strstr(s, "out") != NULL;
  if (isIn)
  {
    if (isOut)
    {
      g_token->paramDir=InOut;
    }
    else
    {
      g_token->paramDir=In;
    }
  }
  else if (isOut)
  {
    g_token->paramDir=Out;
  }
  else
  {
    g_token->paramDir=Unspecified;
  }
  return TK_COMMAND;
}

<St_Para>{WORD1} |
<St_Para>{WORD2} { /* function call */ 
  if (yytext[0]=='%') // strip % if present
    SET_TOKEN_NAME (yytext + 1);
  else
    SET_TOKEN_NAME (yytext);
  return TK_WORD;
}

<St_Para>{BLANK}+      |
<St_Para>{BLANK}*\n{BLANK}* { /* white space */ 
  g_token->chars=yytext;
  return TK_WHITESPACE;
}

<St_Para>({BLANK}*\n)+{BLANK}*\n{BLANK}* {
  g_token->indent=computeIndent(yytext, (int)yyleng);
  int i;
  // put back the indentation (needed for list items)
  for (i=0;i<g_token->indent;i++)
  {
    unput(' ');
  }
  // tell flex that after putting the last indent 
  // back we are at the beginning of the line
  YY_CURRENT_BUFFER->yy_at_bol=1;
  // start of a new paragraph
  return TK_NEWPARA;
}

<St_Param>"\""[^\n\"]+"\"" {
  SET_TOKEN_NAME (g_strstrip (yytext+1));
  return TK_WORD;
}

<St_Param>({PHPTYPE}{BLANK}*"|"{BLANK}*)*{PHPTYPE}{WS}+("&")?"$"{LABELID} {
  SET_TOKEN_NAME (yytext);
  /* FIXME
     int j = params.find('&');
     int i = params.find('$');
     if (j<i && j!=-1) i=j;
     QCString types = params.left(i).stripWhiteSpace();
     g_token->name = types+"#"+params.mid(i);
   */
  return TK_WORD;
}

<St_Param>[^ \t\n,@\\]+  {
  if (yytext[yyleng - 1] == ':') {
    g_string_free (g_token->name, TRUE);
    g_token->name = g_string_new_len (yytext, yyleng - 1);
  } else {
    SET_TOKEN_NAME (yytext);
  }
  return TK_WORD;
}

<St_Param>{WS}*","{WS}*  /* param separator */
<St_Param>{WS}	       {
  g_token->chars=yytext;
  return TK_WHITESPACE;
}

<*>.

<*>\n {
}

%%

//--------------------------------------------------------------------------

void doctokenizerYYinit(const char *input)
{
  g_inputString = input;
  g_inputPos    = 0;
  BEGIN(St_Initial);
}

void doctokenizerYYsetStatePara()
{
  BEGIN(St_Para);
}

void doctokenizerYYsetStateParam()
{
  BEGIN(St_Param);
}

void doctokenizerYYcleanup()
{
  yy_delete_buffer( YY_CURRENT_BUFFER );
}
