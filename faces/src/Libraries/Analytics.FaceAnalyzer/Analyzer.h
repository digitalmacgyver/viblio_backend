/*
	The base class that defines an "Analyzer", a unit of functionality designed to extract a specific type of information (information about faces, places, objects etc)

	Date: 03/07/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#ifndef ___ANALYZER_BASECLASS_H__
#define ___ANALYZER_BASECLASS_H__

#include <opencv2/opencv.hpp>
#include "FaceDetector_OpenCV.h"

namespace Analytics
{

// fwd declarations
//class FaceDetector_OpenCV;

class Analyzer
{
private:
	// no copy constructor or assignment operator
	Analyzer(const Analyzer&);
	Analyzer& operator=(const Analyzer&);

public:
	Analyzer(){};
	virtual ~Analyzer(){};

	virtual void Process(const cv::Mat &frame, uint64_t frameTimestamp) = 0;
};

// end of namespaces
}
#endif 