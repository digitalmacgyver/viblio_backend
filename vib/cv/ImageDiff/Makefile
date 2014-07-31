FILES=imagediff.cpp

all : $(FILES)
	g++ -O3 -std=c++0x -o imagediff $(FILES) `pkg-config opencv --cflags --libs`

clean :
	rm imagediff