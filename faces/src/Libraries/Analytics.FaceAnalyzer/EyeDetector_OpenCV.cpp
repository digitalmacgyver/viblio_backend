/*
	The entry point into the application. Parses command line options (or config files) and sets up the program
	flow based on said options

	Date: 25/06/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#include "EyeDetector_OpenCV.h"

#include <string>
#include <stdexcept>
#include "opencv2/opencv.hpp"

using namespace std;
using namespace cv;

namespace Analytics
{
	namespace FaceAnalyzer
	{

EyeDetector_OpenCV::EyeDetector_OpenCV(const string &eyes_cascade_name)
{
	if( eyes_cascade_name.empty() )
		throw runtime_error("Error eye cascade filename was empty");

	if( !m_eyesCascade.load( eyes_cascade_name ) )
	{ 
		cout << "Error loading eye cascade with filename " << eyes_cascade_name << endl;
		throw runtime_error("Error loading eye cascade with filename " + eyes_cascade_name);
	}
}


EyeDetector_OpenCV::~EyeDetector_OpenCV()
{
}

vector<Rect> EyeDetector_OpenCV::Detect(const Mat &frame)
{
	vector<Rect> eyes;

	m_eyesCascade.detectMultiScale( frame, eyes, 1.1, 2, 0 |CV_HAAR_SCALE_IMAGE, Size(30, 30) );
	
	return eyes;
}

// end of namespaces
	}
}
