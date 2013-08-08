/*
	OpenCV based eye detector.

	Author: Jason Catchpole
*/

#ifndef __EYEDETECTOR_OPENCV__
#define __EYEDETECTOR_OPENCV__

#include "opencv2/objdetect/objdetect.hpp"

namespace Analytics
{
	namespace FaceAnalyzer
	{

class EyeDetector_OpenCV
{
private:
	cv::CascadeClassifier m_eyesCascade;

	EyeDetector_OpenCV(const EyeDetector_OpenCV&);                 // Prevent copy-construction
	EyeDetector_OpenCV& operator=(const EyeDetector_OpenCV&);      // Prevent assignment

public:
	EyeDetector_OpenCV(const std::string &eyes_cascade_name);
	~EyeDetector_OpenCV();

	std::vector<cv::Rect> Detect(const cv::Mat &frame);
};

// end of namespaces
	}
}

#endif