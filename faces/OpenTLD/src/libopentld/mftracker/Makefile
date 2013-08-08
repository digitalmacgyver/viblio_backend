SOURCES=\
BB.cpp\
BBPredict.cpp\
FBTrack.cpp\
Lk.cpp\
Median.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++0x
LIBNAME=libmftracker.a

%.o : %.cpp
	g++ -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

