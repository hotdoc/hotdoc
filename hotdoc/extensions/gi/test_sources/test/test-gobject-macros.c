#include "test-gobject-macros.h"

/**
 * SECTION: test-gobject-macros
 * @title: Derivable and more
 * @short_description: In this file, we test the G_DECLARE_FINAL_TYPE
 * and G_DECLARE_DERIVABLE_TYPE macros.
 *
 * We're particularly interested in smart filtering.
 */
G_DEFINE_TYPE (TestDerivable, test_derivable, G_TYPE_OBJECT)

struct _TestFinal
{
  TestDerivable parent;
};

G_DEFINE_TYPE (TestFinal, test_final, G_TYPE_OBJECT)

static void
test_derivable_class_init (TestDerivableClass *klass)
{
}

static void
test_derivable_init (TestDerivable *self)
{
}

static void
test_final_class_init (TestFinalClass *klass)
{
}

static void
test_final_init (TestFinal *self)
{
}
