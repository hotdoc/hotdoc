#pragma once

#include <glib-object.h>

G_BEGIN_DECLS

typedef struct _ObjObjClass ObjObjClass;
typedef struct _ObjObj ObjObj;

struct _ObjObj
{
  GObject parent;

  const gchar * a_string;
  gpointer _padding[10];
};

struct _ObjObjClass
{
  GObjectClass parent;

  const gchar * a_string;
  gpointer _padding[10];
};

GType obj_obj_get_type (void);

G_END_DECLS
