/*
	Handles the task of configuring the pipeline based on the configuration requirements for this job, and then taking each frame from the video source and 
	passing them through each of the analyzers

	Date: 03/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#ifndef __VIDEO_PROCESSOR__
#define __VIDEO_PROCESSOR__

#include <vector>

#include "JobConfiguration.h"
#include "Analytics.FaceAnalyzer/Analyzer.h"
#include "VideoSource/VideoSource.h"


class VideoProcessor
{
 private:
  // no copy constructor or assignment operator
  VideoProcessor(const VideoProcessor&);
  VideoProcessor& operator=(const VideoProcessor&);

  // the vector of analyzers that will be used for this video processing job
  std::vector<Analytics::Analyzer*> m_analyzers;

  // the video source that will be supplying us with frames for analysis
  VideoSource::VideoSourceBase *m_videoSource;

  bool SetupAnalyzers(const JobConfiguration &jobConfig);

 public:
  VideoProcessor(const JobConfiguration &jobConfig);
  ~VideoProcessor();

  // Do the main work of the job. Takes in each frame, decodes it and then passes it along for analysis and then encoding
  bool PerformProcessing();
};

#endif
