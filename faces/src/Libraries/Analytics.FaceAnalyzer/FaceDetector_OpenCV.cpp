/*
	The entry point into the application. Parses command line options (or config files) and sets up the program
	flow based on said options

	Date: 25/06/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#include "FaceDetector_OpenCV.h"
#include "EyeDetector_OpenCV.h"

#include <opencv2/opencv.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv/highgui.h>

#include <vector>
#include <stdexcept>

using namespace std;
using namespace cv;

namespace Analytics
{
	namespace FaceAnalyzer
	{

FaceDetector_OpenCV::FaceDetector_OpenCV(const string &face_cascade_name, const string &eyes_cascade_name)
{
	if( face_cascade_name.empty() )
		return;

	if( !m_faceCascade.load( face_cascade_name ) )
	{ 
		cout << "Error loading face cascade with filename " << face_cascade_name << endl;
		throw runtime_error("Error loading face cascade with filename " + face_cascade_name);
	}
	
	if( !eyes_cascade_name.empty() )
	{
		try
		{
			m_eyeDetector.reset( new EyeDetector_OpenCV(eyes_cascade_name) );
		}
		catch(Exception e)
		{
			throw e;
		}

		m_filterFacesByEyeDetections = true;
	}
	else
	{
		m_eyeDetector = NULL;
		m_filterFacesByEyeDetections = false;
	}
}


FaceDetector_OpenCV::~FaceDetector_OpenCV()
{
}

vector<Rect> FaceDetector_OpenCV::Detect(const Mat &frame)
{
	vector<Rect> faces;
	Mat frame_gray;

	// this copy of the frame is only needed for debug purposes, can be deleted
	Mat frameCopy;
	frame.copyTo(frameCopy);

	cvtColor( frame, frame_gray, CV_BGR2GRAY );
	equalizeHist( frame_gray, frame_gray );

	//-- Detect faces
	// If you end up using a HAAR cascade here then you should use face_cascade.detectMultiScale( frame_gray, faces, 1.1, 2, 0|CV_HAAR_SCALE_IMAGE, Size(30, 30) );
	m_faceCascade.detectMultiScale( frame_gray, faces, 1.1, 2, 0, Size(80, 80) );

	if( m_filterFacesByEyeDetections )
	{
		vector<Rect> filteredFaces;

		for( unsigned int i = 0; i < faces.size(); i++ )
		{
			Mat faceROI = frame_gray( faces[i] );

			// for each face pass it to the eye detector
			vector<Rect> eyes = m_eyeDetector->Detect(faceROI);
			
			if( eyes.size() == 2) // means we found the two eyes
			{
				filteredFaces.push_back(faces[i]);

				//-- Draw the face
				Point center( faces[i].x + int(faces[i].width*0.5f), faces[i].y + int(faces[i].height*0.5f) );
				ellipse( frameCopy, center, Size( int(faces[i].width*0.5f), int(faces[i].height*0.5f)), 0, 0, 360, Scalar( 255, 0, 0 ), 2, 8, 0 );

				for( unsigned int j = 0; j < eyes.size(); j++ )
				{ //-- Draw the eyes
					Point center( faces[i].x + eyes[j].x + int(eyes[j].width*0.5f), faces[i].y + eyes[j].y + int(eyes[j].height*0.5f) );
					int radius = cvRound( (eyes[j].width + eyes[j].height)*0.25f );
					circle( frameCopy, center, radius, Scalar( 255, 0, 255 ), 3, 8, 0 );
				}
			}
		}

		//-- Show what you got
		//	imshow( "temp", frameCopy );

		return filteredFaces;
	}
	else
	{

	  if(!faces.empty())
	    {
		//-- Draw the face
		Point center( faces[0].x + int(faces[0].width*0.5f), faces[0].y + int(faces[0].height*0.5f) );
		ellipse( frameCopy, center, Size( int(faces[0].width*0.5f), int(faces[0].height*0.5f)), 0, 0, 360, Scalar( 255, 0, 0 ), 2, 8, 0 );
	    }
		//-- Show what you got
		//	imshow( "temp", frameCopy );

		// no filtering so just return the found faces
		return faces;
	}
}

// end of namespaces
	}
}
