/*
	Represents a face being tracked and handles all functionality associated with a face

	Date: 21/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#ifndef __TRACKING_FACE__
#define __TRACKING_FACE__

#include "FaceAnalyzerConfiguration.h"
#include <opencv2/opencv.hpp>
#include <boost/uuid/uuid.hpp>


namespace Analytics
{
  namespace FaceAnalyzer
  {

    // fwd declarations
    class Tracker_OpenTLD;

class Face
{
 private:
  // no copy constructor or assignment operator
  Face(const Face&);
  Face& operator=(const Face&);

  // a unique identifier for this face
  boost::uuids::uuid m_faceId;

  // indicates whether the face has been lost or not, likely due to them leaving the scene or because they
  // are simply out of view of the camera (occluded etc)
  bool m_isLost;

  // indicates whether the face has had recognition applied to them yet
  bool m_hasBeenRecognized;

  // stores a history of the frames location in recent frames (the number of frames in the past it will store is based on the face location history size parameter)
  int m_factLocationHistorySize;
  std::map<uint64_t, cv::Rect> m_faceLocationHistory;

  // a vector of times when the face was visible in the scene. It is a vector of pairs of timestamps when the face entered and left (or was lost track of)
  std::vector<std::pair<uint64_t, uint64_t>> m_timesWhenFaceVisible;
  std::pair<uint64_t, uint64_t> m_currentFaceVisiblePair;
  uint64_t m_mostRecentFrameTimestamp;

  // the tracker that will be used to track this face
  Tracker_OpenTLD *m_faceTracker;
  std::string Thumbnail_path;
 public:
  Face(Tracker_OpenTLD *m_trackerToInitializeFrom, const cv::Mat frame, cv::Rect initialFaceRegion,FaceAnalyzerConfiguration *faceAnalyzerConfig);
  ~Face();

  bool Process(const cv::Mat &frame, uint64_t frameTimestamp);

  boost::uuids::uuid GetFaceId(){ return m_faceId; }
};

// end of namespaces
  }
}

#endif
