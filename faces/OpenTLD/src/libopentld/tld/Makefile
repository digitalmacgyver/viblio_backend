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
CFLAGS=-std=c++11 -I../../3rdparty/cvblobs -I../mftracker
LIBNAME=libOpenTld.a

%.o : %.cpp
	g++-4.7 -c $(CFLAGS) $< -o $@

$(LIBNAME) : $(OBJS)
	ar rcs $@ $^

clean :
	rm -rf $(LIBNAME) $(OBJS)

