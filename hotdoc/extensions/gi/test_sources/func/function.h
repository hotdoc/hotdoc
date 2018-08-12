#pragma once

#include "obj.h"

/**
 * FuncStruct:
 * @ObjObj: object
 */
typedef struct _FuncStruct FuncStruct;

struct _FuncStruct
{
    ObjObj *obj;
};

void func_f1(FuncStruct * str);

char * func_out_arg(FuncStruct *str);
char * func_no_out_arg(FuncStruct *str);
