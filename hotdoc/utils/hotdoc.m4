dnl -*- mode: autoconf -*-

# serial 1

dnl Usage:
dnl HOTDOC_CHECK(EXTENSION, action-if-found, action-if-not-found)
AC_DEFUN([HOTDOC_CHECK_EXTENSION],
[
  AS_IF([test "x$1" = "x"], [$2])

  AC_MSG_CHECKING(for python2 module: $1)

  python2 -c "import $1" 2>/dev/null
  if test $? -eq 0;
  then
  	AC_MSG_RESULT(yes)
  	$2
  else
	AC_MSG_RESULT(no)
	$3
  fi
])

dnl Usage:
dnl HOTDOC_CHECK([EXTENSION, EXTENSION, ...])
AC_DEFUN([HOTDOC_CHECK],
[
  all_exts_found=yes
  AC_ARG_ENABLE([documentation],
                [AS_HELP_STRING([--enable-documentation],
                                [Enable documentation (default: yes)])],
                [enable_documentation=$enableval],
                [enable_documentation=yes])
  AC_PATH_PROG([HOTDOC], [hotdoc], [no])
  AS_IF([test "x$HOTDOC" = "xno" && test "x$enable_documentation" = "xyes"],
        [AC_MSG_ERROR([Could not find the required hotdoc executable,
         you can disable doc generation with --enable-documentation=no or with --disable-documentation])]
  )

  AS_IF([test "x$@" != "x"],
  	[m4_foreach([ext],
		    [$@],
		    [HOTDOC_CHECK_EXTENSION([ext],
		    			    [],
					    [all_exts_found=no])])])

  AS_IF([test "x$all_exts_found" = "xno" && test "x$enable_documentation" = "xyes"],
        [AC_MSG_ERROR([Could not find the required hotdoc extensions,
         you can disable doc generation with --enable-documentation=no or with --disable-documentation])]
  )

  AS_IF([test "x$all_exts_found" = "xno" || test "x$HOTDOC" = "xno"],
  	[enable_documentation=no])

  AM_CONDITIONAL([ENABLE_DOCUMENTATION], [test "x$enable_documentation" != "xno"])
])
