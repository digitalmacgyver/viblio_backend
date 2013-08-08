#ifndef __TRACKER_OPENTLD__
#define __TRACKER_OPENTLD__

#include "opencv2/opencv.hpp"
#include "TLD.h"

namespace Analytics
{
	namespace FaceAnalyzer
	{

class Tracker_OpenTLD
{
private:
	tld::TLD *m_tldTracker;

	float m_confidence;

	// no copy constructor or assignment operator
	Tracker_OpenTLD(const Tracker_OpenTLD&);
	Tracker_OpenTLD& operator=(const Tracker_OpenTLD&);

public:
	Tracker_OpenTLD();
	~Tracker_OpenTLD();

	void InitialiseTrack(const cv::Mat &frame, cv::Rect &boundingRegion);

	cv::Rect Process(const cv::Mat &frame);

	// Returns the confidence in the most recently processed frame
	float GetConfidence(){ return m_confidence; }

	void EnableAlternating();
};

// end of namespaces
	}
}

#endif
