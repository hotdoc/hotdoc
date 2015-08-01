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

#ifndef _DOCTOKENIZER_H
#define _DOCTOKENIZER_H

#include <stdio.h>
#include <stdbool.h>
#include <glib.h>

typedef struct _Definition Definition;
typedef struct _MemberGroup MemberGroup;
typedef struct
{
} HtmlAttribList;

enum Tokens
{
  TK_WORD          = 1,
  TK_WHITESPACE    = 2,
  TK_COMMAND       = 3,
  TK_NEWPARA       = 4,

  RetVal_OK             = 0x10000,
  RetVal_SimpleSec      = 0x10001,
  RetVal_ListItem       = 0x10002,
  RetVal_Section        = 0x10003,
  RetVal_Subsection     = 0x10004,
  RetVal_Subsubsection  = 0x10005,
  RetVal_Paragraph      = 0x10006,
  RetVal_SubParagraph   = 0x10007,
  RetVal_EndList        = 0x10008,
  RetVal_EndPre         = 0x10009,
  RetVal_DescData       = 0x1000A,
  RetVal_DescTitle      = 0x1000B,
  RetVal_EndDesc        = 0x1000C,
  RetVal_TableRow       = 0x1000D,
  RetVal_TableCell      = 0x1000E,
  RetVal_TableHCell     = 0x1000F,
  RetVal_EndTable       = 0x10010,
  RetVal_Internal       = 0x10011,
  RetVal_SwitchLang     = 0x10012,
  RetVal_CloseXml       = 0x10013,
  RetVal_EndBlockQuote  = 0x10014,
  RetVal_CopyDoc        = 0x10015,
  RetVal_EndInternal    = 0x10016,
  RetVal_EndParBlock    = 0x10017
};

typedef enum {
  Page          = 0,
  Section       = 1,
  Subsection    = 2,
  Subsubsection = 3,
  Paragraph     = 4,
  Anchor        = 5
} SectionType;

typedef enum 
{ In=1,
  Out=2,
  InOut=3,
  Unspecified=0 }
  ParamDir;

  /** @brief Data associated with a token used by the comment block parser. */
  typedef struct
{
  // unknown token
  char unknownChar;

  // command token
  //char *name;
  GString *name;

  // command text (RCS tag)
  char *text;

  // list token info
  bool isEnumList;
  int indent;

  // sections
  char *sectionId;

  // simple section
  char *simpleSectName;
  char *simpleSectText;

  // verbatim fragment
  char *verb;

  // xrefitem
  int id;

  // html tag
  HtmlAttribList attribs;
  bool endTag;
  bool emptyTag;

  // whitespace
  char *chars;

  // url
  bool isEMailAddr;

  // param attributes
  ParamDir paramDir;
} TokenInfo;

// globals
extern TokenInfo *g_token;
extern int doctokenizerYYlineno;
extern FILE *doctokenizerYYin;

// helper functions
const char *tokToString(int token);

// operations on the scanner
void doctokenizerYYinit(const char *input);
void doctokenizerYYcleanup();
int  doctokenizerYYlex();
void doctokenizerYYsetStatePara();
void doctokenizerYYsetStateTitle();
void doctokenizerYYsetStateTitleAttrValue();
void doctokenizerYYsetStateCode();
void doctokenizerYYsetStateXmlCode();
void doctokenizerYYsetStateHtmlOnly();
void doctokenizerYYsetStateManOnly();
void doctokenizerYYsetStateLatexOnly();
void doctokenizerYYsetStateXmlOnly();
void doctokenizerYYsetStateDbOnly();
void doctokenizerYYsetStateRtfOnly();
void doctokenizerYYsetStateVerbatim();
void doctokenizerYYsetStateDot();
void doctokenizerYYsetStateMsc();
void doctokenizerYYsetStateParam();
void doctokenizerYYsetStateXRefItem();
void doctokenizerYYsetStateFile();
void doctokenizerYYsetStatePattern();
void doctokenizerYYsetStateLink();
void doctokenizerYYsetStateCite();
void doctokenizerYYsetStateRef();
void doctokenizerYYsetStateInternalRef();
void doctokenizerYYsetStateText();
void doctokenizerYYsetStateSkipTitle();
void doctokenizerYYsetStateAnchor();
void doctokenizerYYsetInsidePre(bool b);
void doctokenizerYYpushBackHtmlTag(const char *tag);
void doctokenizerYYsetStateSnippet();
void doctokenizerYYstartAutoList();
void doctokenizerYYendAutoList();
void doctokenizerYYsetStatePlantUML();
void doctokenizerYYsetStateSetScope();
void doctokenizerYYsetStatePlantUMLOpt();

/* FIXME */
char *realloc_and_concat(char *str, char *s2);

#endif
