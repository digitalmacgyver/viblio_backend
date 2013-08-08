all : cvblobs tld mftracker analytics FileSystem VideoSource viblio

cvblobs : 
	cd OpenTLD/src/3rdparty/cvblobs ; make ; cd ../../../../

tld : 
	cd OpenTLD/src/libopentld/tld ; make ; cd ../../../../

mftracker : 
	cd OpenTLD/src/libopentld/mftracker ; make ; cd ../../../../

analytics : 
	cd src/Libraries/Analytics.FaceAnalyzer ; make ; cd ../../../

FileSystem : 
	cd src/Libraries/FileSystem ; make ; cd ../../../

VideoSource :
	cd src/Libraries/VideoSource ; make ; cd ../../../

viblio : 
	cd src/apps/viblio_video_analyzer; make ; cd ../../../

clean : 
	cd OpenTLD/src/3rdparty/cvblobs ; make clean ; cd ../../../../
	cd OpenTLD/src/libopentld/tld ; make clean ; cd ../../../../
	cd OpenTLD/src/libopentld/mftracker ; make clean ; cd ../../../../
	cd src/Libraries/Analytics.FaceAnalyzer ; make clean ; cd ../../../
	cd src/Libraries/FileSystem ; make clean ; cd ../../../
	cd src/Libraries/VideoSource ; make clean ; cd ../../../
	cd src/apps/viblio_video_analyzer; make clean ; cd ../../../
