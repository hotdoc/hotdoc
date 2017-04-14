# hotdoc.m4 - Macros to locate and utilise hotdoc.            -*- Autoconf -*-
# serial 2 (hotdoc 0.7.10)
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>.
# Copyright © 2016 Collabora Ltd.
# Written by Mathieu Duponchelle
#
# Copying and distribution of this file, with or without modification,
# is permitted in any medium without royalty provided the copyright
# notice and this notice are preserved.
#
# The latest version of this file is maintained in hotdoc itself, at
# <https://github.com/hotdoc/hotdoc/blob/master/hotdoc/utils/hotdoc.m4>

m4_define([_HOTDOC_CHECK_INTERNAL],
[
	m4_if([$2], [require],
	      [enable_documentation=yes],
	      [AC_ARG_ENABLE(documentation,
                  	     AS_HELP_STRING([--enable-documentation[=@<:@no/auto/yes@:>@]],
                             		    [Enable documentation for this build]),, 
                             		    [enable_documentation=auto])
	      ])

	AS_IF([test "x$enable_documentation" = "xno"],
	      [HOTDOC="no"],
	      [AC_PATH_PROG([HOTDOC],
	      		    [hotdoc],
			    [no])])

	AS_IF([test "x$HOTDOC" != "xno"],
	      [AS_VERSION_COMPARE([`$HOTDOC --version`],[$1],
	      	     [HOTDOC="no"])])


	have_all_exts="yes"

	AS_IF([test "x$HOTDOC" != "xno"],
	      [m4_foreach([ext], [$3],
	      		  AC_MSG_CHECKING([[for the hotdoc] ext [extension]])
			  [AS_IF([$HOTDOC --has-extension ext >/dev/null],
				 [AC_MSG_RESULT([yes])],
			   	 [AC_MSG_RESULT([no])
				  have_all_exts="no"])
			  ]
  	      )]
	      )

	AS_IF([test "x$have_all_exts" = "xno"],
	      [HOTDOC="no"])

	AS_IF([test "x$HOTDOC" = "xno" && test "x$enable_documentation" = "xyes"],
	      [AC_MSG_ERROR([check your hotdoc install, or disable documentation \
with --disable-documentation.])])

	AS_IF([test "x$HOTDOC" = "xno"],
	      [enable_documentation=no],
	      [enable_documentation=yes])

	AS_IF([test "x$HOTDOC" != "xno"],
	      [HOTDOC_MAKEFILE=`$HOTDOC --makefile-path`])

	AC_SUBST(HOTDOC_MAKEFILE)

	AM_CONDITIONAL([ENABLE_DOCUMENTATION], [test "x$enable_documentation" = "xyes"])
])

# HOTDOC_CHECK(VERSION, [EXTENSIONS])
#
# Check to see if hotdoc is available, is at least at the specified version,
# and all the specified extensions are available.
#
# Also add a --enable-documentation argument to configure.
#
# EXTENSIONS is a comma-separated list of hotdoc extensions, for example:
#
# [c, gi, dbus]
#
# If all goes well:
# HOTDOC is set to the absolute path to hotdoc
# enable_documentation is set to yes, mostly for pretty-printing purposes
# the automake conditional ENABLE_DOCUMENTATION will return true when tested.
#
# Otherwise:
# HOTDOC is set to no
# enable_documentation is set to no
# the automake conditional ENABLE_DOCUMENTATION will return false when tested.
# If yes was passed to enable-documentation, errors out with a message

AC_DEFUN([HOTDOC_CHECK],
[
  _HOTDOC_CHECK_INTERNAL([$1], [], [$2])
])

# HOTDOC_REQUIRE(VERSION, [EXTENSIONS])
#
# Same as HOTDOC_CHECK with enable-documentation set to yes, and the
# --enable-documentation argument isn't added.
#
# Use this if you want to make building of the documentation mandatory
AC_DEFUN([HOTDOC_REQUIRE],
[
  _HOTDOC_CHECK_INTERNAL([$1], [require], [$2])
])
