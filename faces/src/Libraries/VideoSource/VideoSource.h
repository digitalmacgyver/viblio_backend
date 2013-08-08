/*
*	The definition of a base class that all video sources inherit from. Defines the interface common to all sources
*	of video
*
*	Author: Jason Catchpole
*/

#ifndef __VIBLIO_VIDEOSOURCE__
#define __VIBLIO_VIDEOSOURCE__

#include <opencv2/opencv.hpp>


namespace VideoSource
{

class VideoSourceBase
{
 private:
  // no copy constructor or assignment operator
  VideoSourceBase(const VideoSourceBase&);
  VideoSourceBase& operator=(const VideoSourceBase&);

 public:
  VideoSourceBase(){};
  virtual ~VideoSourceBase(){};

  // Returns true if a new frame can be read (with GetNextFrame) or false if a frame is not yet available
  virtual bool NextFrameReady() = 0;

  // Returns the next frame from the video source
  virtual cv::Mat GetNextFrame() = 0;

  virtual int NumberFrames() = 0;
  virtual uint64_t GetTimestamp() = 0;
};

// end of namespaces
}

#endif
