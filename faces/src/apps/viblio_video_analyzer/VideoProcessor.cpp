/*
	Handles the task of configuring the pipeline based on the configuration requirements for this job, and then taking each frame from the video source and 
	passing them through each of the analyzers

	Date: 03/07/2013

	Author: Jason Catchpole
*/

#include "VideoProcessor.h"
#include "JobConfiguration.h"
#include "VideoSource/FileVideoSource.h"
#include "Analytics.FaceAnalyzer/FaceAnalyzer.h"
#include "FileSystem/FileSystem.h"

#include <opencv2/opencv.hpp>
#include <string>

using namespace std;
using namespace cv;


VideoProcessor::VideoProcessor(const JobConfiguration &jobConfig)
{
  // go through all the config, ensure sane values, ensure input paths/files exist, ensure output paths exist (and are writable).
  // If there are any problems log it and then throw an exception

  // setup the video source based on the type of the source specified by the job
  try
    {
      m_videoSource = new VideoSource::FileVideoSource(jobConfig.videoSourceFilename);
    }
  catch(Exception e)
    {
      cout << "Exception caught while attempting to create the FileVideoSource. Message = " << e.msg << ". Cannot continue" << endl;
      throw e;
    }



  // pull info out of the job config as to all the Analyzers they want to use in this job and then call SetupAnalyzers to actually initialize/configure each of them
  SetupAnalyzers(jobConfig);
}

VideoProcessor::~VideoProcessor()
{
  if( m_videoSource )
    {
      delete m_videoSource;
      m_videoSource = NULL;
    }

  // go through each of the analyzers and deallocate them
}

bool VideoProcessor::SetupAnalyzers(const JobConfiguration &jobConfig)
{
  // for each analyzer that we implement we should log the configuration options used to set the analyzer up (each AnalyzerConfig should
  // implement the ToString() method

  if( jobConfig.isFaceAnalyzerEnabled )
    {
      if( jobConfig.faceAnalyzerConfig == NULL )
	cout << "Error - Face Analyzer is enabled but configuration information is not present" << endl;
      else
	m_analyzers.push_back(new Analytics::FaceAnalyzer::FaceAnalysis(jobConfig.faceAnalyzerConfig));
    }

  return true;
}

bool VideoProcessor::PerformProcessing()
{

  // go through each frame from the video source and pass it along to each of the analyzers
  Mat currentFrame;
  uint64_t timestamp;
  while(true)
    {
      currentFrame = m_videoSource->GetNextFrame();
      timestamp = m_videoSource->GetTimestamp();
      // Printing the current Timestamp
      cout<< "Time stamp : " << timestamp<<endl;
      if( currentFrame.empty() )
	break;

      // pass to each of the analyzers - could be performed in parallel assuming each analyzer is independent (which it should be)
      for(vector<Analytics::Analyzer*>::iterator startIter=m_analyzers.begin(); startIter != m_analyzers.end(); ++startIter)
	(*startIter)->Process(currentFrame,timestamp); // replace the 0 here with the actual frame timestamp

      // imshow("Current frame", currentFrame);
      waitKey(5);

    }

  return true;
}
