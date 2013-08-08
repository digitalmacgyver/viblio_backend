SOURCES=FileVideoSource.cpp
OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++0x -I../
LIBNAME=libVideoSource.a

%.o : %.cpp
	g++ -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

