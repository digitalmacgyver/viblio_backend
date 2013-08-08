SOURCES=\
EyeDetector_OpenCV.cpp\
FaceAnalyzerConfiguration.cpp\
FaceAnalyzer.cpp\
Face.cpp\
FaceDetector_OpenCV.cpp\
Tracker_OpenTLD.cpp\
TrackingController.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++11 -I../ -I../../../OpenTLD/src/libopentld/tld/
LIBNAME=libFaceAnalyzer.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

