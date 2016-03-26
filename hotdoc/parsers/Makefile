SCANNERS = cmark_gtkdoc_scanner.c \
	   cmark_include_scanner.c \
	   $(NULL)

%.c: %.re
	re2c --case-insensitive -b -i --no-generation-date -8 --encoding-policy substitute -o $@ $<

all: $(SCANNERS)

clean:
	rm -f $(SCANNERS)
