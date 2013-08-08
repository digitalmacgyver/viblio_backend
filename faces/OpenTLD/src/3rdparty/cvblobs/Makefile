SOURCES=\
BlobContour.cpp\
blob.cpp\
BlobOperators.cpp\
BlobProperties.cpp\
BlobResult.cpp\
ComponentLabeling.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++0x
LIBNAME=libcvblobs.a

%.o : %.cpp
	g++ -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

