/*
	The base class that defines an "AnalyzerConfig", configuration information used to setup and specify
	the operation of a given class of analyzer

	Date: 04/07/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#ifndef ___ANALYZERCONFIG_BASECLASS_H__
#define ___ANALYZERCONFIG_BASECLASS_H__

#include <opencv2/opencv.hpp>
#include "FaceDetector_OpenCV.h"

namespace Analytics
{

class AnalyzerConfig
{
private:
	// no copy constructor or assignment operator
	AnalyzerConfig(const AnalyzerConfig&);
	AnalyzerConfig& operator=(const AnalyzerConfig&);

public:
	AnalyzerConfig(){};
	virtual ~AnalyzerConfig(){};

	// this method must be implemented by each of the child classes as it is used when logging out the configuration
	// that each analyzer used for this job
	virtual std::string ToString() = 0;
};

// end of namespaces
}
#endif 