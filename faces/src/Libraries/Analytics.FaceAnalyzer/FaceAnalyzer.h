#ifndef __FACE_ANALYSIS_ANALYZER_H__
#define __FACE_ANALYSIS_ANALYZER_H__

#include <memory>
#include <opencv2/opencv.hpp>
#include "Analyzer.h"
//#include "FaceDetector_OpenCV.h"

namespace Analytics
{
	namespace FaceAnalyzer
	{

// fwd declarations
class FaceAnalyzerConfiguration;
class FaceDetector_OpenCV;
class TrackingController;

class FaceAnalysis : public Analyzer
{
private:
	// The face detector we will use to identify faces in a given frame
	std::unique_ptr<FaceDetector_OpenCV> m_faceDetector;

	std::unique_ptr<TrackingController> m_trackingController;

	// no copy constructor or assignment operator
	FaceAnalysis(const FaceAnalysis&);
	FaceAnalysis& operator=(const FaceAnalysis&);

public:
	FaceAnalysis(FaceAnalyzerConfiguration *faceAnalyzerConfig);
	~FaceAnalysis();

	void Process(const cv::Mat &frame, uint64_t frameTimestamp);
};

// end of namespaces
	}
}
#endif 