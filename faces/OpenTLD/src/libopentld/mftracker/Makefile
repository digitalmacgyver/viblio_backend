SOURCES=\
BB.cpp\
BBPredict.cpp\
FBTrack.cpp\
Lk.cpp\
Median.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++11 
LIBNAME=libmftracker.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

