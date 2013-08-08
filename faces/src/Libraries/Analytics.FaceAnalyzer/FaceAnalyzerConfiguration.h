/*
	The class defines al the configuration data required for the face analyzer to run 
	(some of the data is optional)

	Date: 06/07/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#ifndef ___FACEANALYZER_CONFIG_H__
#define ___FACEANALYZER_CONFIG_H__

#include "AnalyzerConfig.h"

namespace Analytics
{
	namespace FaceAnalyzer
	{

class FaceAnalyzerConfiguration : public AnalyzerConfig
{
private:
	// no copy constructor or assignment operator
	FaceAnalyzerConfiguration(const FaceAnalyzerConfiguration&);
	FaceAnalyzerConfiguration& operator=(const FaceAnalyzerConfiguration&);

public:
	FaceAnalyzerConfiguration();
	~FaceAnalyzerConfiguration();

	// so we can log all the parameters used for this job
	std::string ToString();

	// the file path for the face detector cascade file to use
	std::string faceDetectorCascadeFile;

	// the file path for the face detector cascade file to use
	std::string eyeDetectorCascadeFile;

	// a path to the location where to write the thumbnails that are extracted
	std::string faceThumbnailOutputPath;
};


// end of namespaces
	}
}

#endif