/*
	OpenCV based face detector.

	Date: 25/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#ifndef __FACEDETECTOR_OPENCV__
#define __FACEDETECTOR_OPENCV__

#include <memory>
#include <opencv2/objdetect/objdetect.hpp>
#include <string>
//#include "EyeDetector_OpenCV.h"

namespace Analytics
{
	namespace FaceAnalyzer
	{

// forward prototypes of used classes
class EyeDetector_OpenCV;

class FaceDetector_OpenCV
{
private:
	cv::CascadeClassifier m_faceCascade;

	bool m_filterFacesByEyeDetections;
	std::unique_ptr<EyeDetector_OpenCV> m_eyeDetector;

	// no copy constructor or assignment operator
	FaceDetector_OpenCV(const FaceDetector_OpenCV&);
	FaceDetector_OpenCV& operator=(const FaceDetector_OpenCV&);

public:
	FaceDetector_OpenCV(const std::string &face_cascade_name, const std::string &eyes_cascade_name="");
	~FaceDetector_OpenCV();

	/*
		Performs detection on the opencv frame passed in. Returns a vector of rects with the locations of any faces detected (empty if no faces detected)
	*/
	std::vector<cv::Rect> Detect(const cv::Mat &frame);
};

// end of namespaces
	}
}
#endif