SOURCES=\
EyeDetector_OpenCV.cpp\
FaceAnalyzerConfiguration.cpp\
FaceAnalyzer.cpp\
Face.cpp\
FaceDetector_OpenCV.cpp\
Tracker_OpenTLD.cpp\
TrackingController.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++0x -I../ -I../../../OpenTLD/src/libopentld/tld/
LIBNAME=libFaceAnalyzer.a

%.o : %.cpp
	g++ -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

