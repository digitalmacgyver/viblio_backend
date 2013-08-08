/*
	Defines and stores the configuration information for this job as provided by the user/caller

	Date: 03/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#ifndef __JOB_CONFIGURATION__
#define __JOB_CONFIGURATION__

#include <memory>
#include <string>
#include "VideoSource/VideoSourceTypes.h"


// forward declarations of all the various configuration types we will be using in this class
namespace Analytics {
  namespace FaceAnalyzer {
    class FaceAnalyzerConfiguration;
  }
}

class JobConfiguration
{
 private:
  // no copy constructor or assignment operator
  JobConfiguration(const JobConfiguration&);
  JobConfiguration& operator=(const JobConfiguration&);

 public:
  JobConfiguration()
    {
      // initialize all the member variables
      isFaceAnalyzerEnabled = false;

      isSceneAnalyzerEnabled = false;

      isEncodingEnabled = false; // encoding disabled unless told otherwise
    }

  // information about the video source that we will be getting the frames from
  VideoSource::VideoSourceTypes videoSourceType;
  std::string videoSourceFilename;

  // ANALYZER INFORMATION
  // information about all the Analyzers that will be used in this job and specific configuration for each analyzer

  // Face Analyzer - Determines who is in the video
  bool isFaceAnalyzerEnabled;
  Analytics::FaceAnalyzer::FaceAnalyzerConfiguration *faceAnalyzerConfig;

  // Scene Analyzer - Tries to determines where the video is captured
  bool isSceneAnalyzerEnabled;

  // Object Analyzer - Determines what objects are seen in the video

  // Action Analyzer - Determines what is happening in the video

  // information about the encoding to be used for this job, target bitrate, resolution, codec, output file path etc
  bool isEncodingEnabled;

  // information about the output for this job, paths, output format etc

};

#endif
