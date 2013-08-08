/*
	A VideoSource where video (and in the future audio) are loaded in from a file from disk

	Date: 01/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#include "FileVideoSource.h"
#include "FileSystem/FileSystem.h"
#include <stdexcept>

using namespace cv;
using namespace std;


namespace VideoSource
{

  FileVideoSource::FileVideoSource(const string &filename) : VideoSourceBase()
  {
    // check to make sure the file actually exists otherwise throw an exception
    // ensure the input file actually exists
    if( !FileSystem::FileExists( filename ) )
      throw runtime_error("File " + filename + " does not exist");

    // it exists so now try and create the OpenCV VideoCapture which will provide access to reading 
    m_videoFile.reset( new VideoCapture(filename) );

    if( !m_videoFile->isOpened() )
      {
	throw runtime_error("File " + filename + " could not be opened");
      }


  }


  FileVideoSource::~FileVideoSource()
  {
    m_videoFile->release();
  }

  // Returns the next frame from the video source
  cv::Mat FileVideoSource::GetNextFrame()
  {
    Mat newFrame;
    m_videoFile->read(newFrame);
    return newFrame;
  }

  int FileVideoSource::NumberFrames()
  {
    // not yet implemented
    return -1;
  }

  uint64_t FileVideoSource::GetTimestamp()
  {
    // returns timestamp in milliseconds appended with "Frame_"
    //std::string frame_timestamp;
    //frame_timestamp="Frame_"+std::to_string(m_videoFile->get(CV_CAP_PROP_POS_MSEC));
    return m_videoFile->get(CV_CAP_PROP_POS_MSEC);
  }

}
