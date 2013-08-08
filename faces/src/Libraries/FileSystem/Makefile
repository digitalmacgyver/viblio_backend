SOURCES=FileSystem.cpp
OBJS=$(SOURCES:.cpp=.o)
CFLAGS=
LIBNAME=libFileSystem.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean : 
	rm -rf $(OBJS) $(LIBNAME)

