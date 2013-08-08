SOURCES=FileVideoSource.cpp
OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++11 -I../
LIBNAME=libVideoSource.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

