SOURCES=\
Clustering.cpp\
DetectionResult.cpp\
DetectorCascade.cpp\
EnsembleClassifier.cpp\
ForegroundDetector.cpp\
MedianFlowTracker.cpp\
NNClassifier.cpp\
TLD.cpp\
TLDUtil.cpp\
VarianceFilter.cpp

OBJS=$(SOURCES:.cpp=.o)
CFLAGS=-std=c++0x -I../../3rdparty/cvblobs -I../mftracker -fpermissive
LIBNAME=libOpenTld.a

%.o : %.cpp
	g++ -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

