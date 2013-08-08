#include "Tracker_OpenTLD.h"

using namespace cv;
using namespace tld;

namespace Analytics
{
	namespace FaceAnalyzer
	{

Tracker_OpenTLD::Tracker_OpenTLD()
{
	m_confidence = 0.0f;

	m_tldTracker = new TLD();
	m_tldTracker->trackerEnabled = true;
	m_tldTracker->alternating = true;
	m_tldTracker->learningEnabled = true;

	// these parameters must be set before calling selectObject in the initialization function as
	// in selectObject it initializes several internal parameters (such as numWindows) which uses the detector cascade
	// shift parameter, and min scale & max scale etc

	m_tldTracker->detectorCascade->varianceFilter->enabled = true;
    m_tldTracker->detectorCascade->ensembleClassifier->enabled = true;
    m_tldTracker->detectorCascade->nnClassifier->enabled = true;

    // classifier
    m_tldTracker->detectorCascade->useShift = true;
    m_tldTracker->detectorCascade->shift = 0.1f;
    m_tldTracker->detectorCascade->minScale = -10;
    m_tldTracker->detectorCascade->maxScale = 10;
    m_tldTracker->detectorCascade->minSize = 25;
    m_tldTracker->detectorCascade->numTrees = 10;
    m_tldTracker->detectorCascade->numFeatures = 10;
    m_tldTracker->detectorCascade->nnClassifier->thetaTP = 0.65f;
    m_tldTracker->detectorCascade->nnClassifier->thetaFP = 0.5f;
}


Tracker_OpenTLD::~Tracker_OpenTLD()
{
	if( m_tldTracker != NULL )
		delete m_tldTracker;
}

void Tracker_OpenTLD::InitialiseTrack(const Mat &frame, Rect &boundingRegion)
{
	// before we call the selectObject function we must call the Process function as it sets up
	// a variety of internal parameters (internal to OpenTLD) used when selectObject is called
	Process(frame);

	Mat gray;
	cvtColor(frame, gray, CV_BGR2GRAY);

	m_tldTracker->detectorCascade->imgWidth = gray.cols;
    m_tldTracker->detectorCascade->imgHeight = gray.rows;
    m_tldTracker->detectorCascade->imgWidthStep = gray.step;

	m_tldTracker->selectObject(gray, &boundingRegion);
}

void Tracker_OpenTLD::EnableAlternating()
{
	m_tldTracker->alternating = true;
}

Rect Tracker_OpenTLD::Process(const Mat &frame)
{
	Mat frameCopy = frame.clone();
	static int currentFrameNumber = 1;

	m_tldTracker->processImage(frame);

	Rect trackingRect = Rect(0,0,0,0);

	m_confidence = m_tldTracker->currConf;

	if( m_tldTracker->currBB != NULL )
	{
		trackingRect = Rect(*(m_tldTracker->currBB));

		//return trackingRect;
	}

	double threshold = 0.7f;
	int confident = (m_confidence >= threshold) ? 1 : 0;

	char statusString[128];
	char learningString[10] = "";
	double fps = 0.0f;

	if(m_tldTracker->learning)
	{
		strcpy(learningString, "Learning");
	}

	sprintf(statusString, "#%d,Posterior %.2f; fps: %.2f, #numwindows:%d, %s", currentFrameNumber - 1, m_tldTracker->currConf, fps, m_tldTracker->detectorCascade->numWindows, learningString);
	CvScalar yellow = CV_RGB(255, 255, 0);
	CvScalar blue = CV_RGB(0, 0, 255);
	CvScalar black = CV_RGB(0, 0, 0);
	CvScalar white = CV_RGB(255, 255, 255);

	if(m_tldTracker->currBB != NULL)
	{
		CvScalar rectangleColor = (confident) ? blue : yellow;
		rectangle(frameCopy, *(m_tldTracker->currBB), rectangleColor, 8, 8, 0);
	}


	//CvFont font;
	//cvInitFont(&font, CV_FONT_HERSHEY_SIMPLEX, .5, .5, 0, 1, 8);
	rectangle(frameCopy, cvPoint(0, 0), cvPoint(frameCopy.cols, 50), black, CV_FILLED, 8, 0);
	putText(frameCopy, statusString, cvPoint(25, 25), FONT_HERSHEY_SIMPLEX, 1.0f, white);

	  //imshow("Tracking Window", frameCopy);

	return trackingRect;
}

// end of namespaces
	}
}
