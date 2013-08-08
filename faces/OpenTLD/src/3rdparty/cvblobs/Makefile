SOURCES=\
BlobContour.cpp\
blob.cpp\
BlobOperators.cpp\
BlobProperties.cpp\
BlobResult.cpp\
ComponentLabeling.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++11 
LIBNAME=libcvblobs.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

