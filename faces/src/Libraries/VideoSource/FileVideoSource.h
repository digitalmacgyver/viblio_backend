#ifndef __FILE_VIDEOSOURCE__
#define __FILE_VIDEOSOURCE__

#include <memory>
#include "VideoSource.h"


namespace VideoSource
{

  class FileVideoSource : public VideoSourceBase
  {
  private:
    std::unique_ptr<cv::VideoCapture> m_videoFile;

    // no copy constructor or assignment operator
    FileVideoSource(const FileVideoSource&);
    FileVideoSource& operator=(const FileVideoSource&);

  public:
    FileVideoSource(const std::string &filename);
    ~FileVideoSource();

    // For file video sources the next frame is always available and ready
    virtual bool NextFrameReady(){ return true; };

    // Returns the next frame from the file
    virtual cv::Mat GetNextFrame();

    // Returns the total number of frames in this file
    virtual int NumberFrames();

    //Returns the timestamp in milliseconds
    virtual uint64_t GetTimestamp();
  };

} // end of namespace

#endif
