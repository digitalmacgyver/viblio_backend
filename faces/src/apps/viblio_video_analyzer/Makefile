SOURCES=\
viblio_video_analyzer.cpp\
VideoProcessor.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++11 -I../../Libraries
EXECNAME=viblio_video_analyzer

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(EXECNAME) : $(OBJS)
	g++-4.7 -std=c++11 -o $@ $(OBJS) -L../../Libraries/FileSystem -L../../Libraries/VideoSource -L../../Libraries/Analytics.FaceAnalyzer/ -L../../../../faces/OpenTLD/src/libopentld/tld/ -L../../../../faces/OpenTLD/src/3rdparty/cvblobs/ -L../../../../faces/OpenTLD/src/libopentld/mftracker -lVideoSource -lFaceAnalyzer -lFileSystem -lOpenTld -lopencv_imgproc -lopencv_core -lcvblobs -lmftracker -lopencv_highgui -lopencv_objdetect -lboost_program_options -lboost_system -lboost_filesystem -lopencv_video

clean :
	rm -rf $(EXECNAME) $(OBJS)

