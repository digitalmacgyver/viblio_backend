/*
	The entry point into the application. Parses command line options (or config files) and sets up the program
	flow based on said options

	Date: 01/07/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#include "boost/program_options.hpp"

#include <iostream>
#include <list>
#include <vector>
#include <stdio.h>
#include <string>

#include "FileSystem/FileSystem.h"
#include "VideoSource/FileVideoSource.h"
#include "Analytics.FaceAnalyzer/AnalyzerTypes.h"
#include "JobConfiguration.h"
#include "Analytics.FaceAnalyzer/FaceAnalyzerConfiguration.h"
#include "VideoProcessor.h"

namespace po = boost::program_options;
using namespace std;
using namespace cv;


// function prototypes
void ExtractFaceAnalysisParameters( po::variables_map variableMap, Analytics::FaceAnalyzer::FaceAnalyzerConfiguration *faceAnalyzer);

int g_verbosityLevel = 0;

int main(int argc, char* argv[])
{
  // Declare the supported options.
  po::options_description desc("Allowed options");
  desc.add_options()
    ("help", "produce help message")
    ("filename,f", po::value<string>(), "specify the input video filename to analyze")
    ("verbosity,v", po::value<int>(&g_verbosityLevel)->default_value(0), "set the verbosity level (between 0-3, 0 is off, 3 is most verbose)")
    ("analyzers", po::value< vector<string> >(), "analyzers to use. Options include \"FaceAnalysis\"")
    ("face_detector_cascade_file", po::value<string>(), "the path to the cascade file to use for face detection")
    ("eye_detector_cascade_file", po::value<string>(), "the path to the cascade file to use for eye detection")
    ("face_thumbnail_path", po::value<string>(), "the location to put output facial thumbnails generated")
    ;

  po::variables_map variableMap;
  po::store(po::parse_command_line(argc, argv, desc), variableMap);
  po::notify(variableMap);    

  // they asked for help, lets give it to them
  if (variableMap.count("help")) 
    {
      cout << desc << "\n";
      return 1;
    }

  cout << "OpenCV version: " << CV_VERSION << endl;

  // If we want to test directory creation..............
  //std::string folder= "RamsriGolla";
  //bool file;
  //FileSystem::CreateDirectory(folder);
  //

  JobConfiguration jobConfig;

  if (variableMap.count("filename")) 
    {
      cout << "Input filename to analyze was set to " 
	   << variableMap["filename"].as<string>() << endl;

      jobConfig.videoSourceFilename = variableMap["filename"].as<string>();
    } 
  else 
    {
      cout << "Input filename not specified, nothing to do" << endl;
      return 1;
    }




  // Analyzer config extraction from parameters and config file
  if( variableMap.count("analyzers") )
    {
      vector<string>::const_iterator startIter = variableMap["analyzers"].as<vector<string>>().begin();
      vector<string>::const_iterator endIter = variableMap["analyzers"].as<vector<string>>().end();
      for(; startIter!=endIter; startIter++)
	{
	  // convert the string to lower case first
	  //std::transform((*startIter).begin(), (*startIter).end(), (*startIter).begin(), ::tolower);

	  // check to see if this value passed in by the user is known to us
	  Analytics::AnalyzerType analyzerType = Analytics::ConvertStringToAnalyzerType(*startIter);
	  if( analyzerType == Analytics::UnknownAnalyzer )
	    {
	      cout << "Error - The specified analyzer named " << *startIter << " is not valid" << endl;
	    }
	  else
	    {
	      // we know what kind of analyzer this is so examine the variable map for the corresponding config for this analyzer
	      switch(analyzerType)
		{
		case Analytics::Analyzer_FaceAnalysis:
		  {
		    jobConfig.isFaceAnalyzerEnabled = true;
		    jobConfig.faceAnalyzerConfig = new Analytics::FaceAnalyzer::FaceAnalyzerConfiguration();
		    ExtractFaceAnalysisParameters( variableMap, jobConfig.faceAnalyzerConfig );
		  } break;
		default:
		  {
		    // do nothing
		  } break;
		};
	    }
	}
    }

  // now that we have all our config data nice and neat lets start processing
  VideoProcessor videoProcessor(jobConfig);

  videoProcessor.PerformProcessing();


  return 0;
}

void ExtractFaceAnalysisParameters( po::variables_map variableMap, Analytics::FaceAnalyzer::FaceAnalyzerConfiguration *faceAnalyzerConfig )
{
  if( faceAnalyzerConfig == NULL )
    return; // can't do aything

  if (variableMap.count("face_detector_cascade_file")) 
    {
      faceAnalyzerConfig->faceDetectorCascadeFile = variableMap["face_detector_cascade_file"].as<string>();
    }

  if (variableMap.count("eye_detector_cascade_file")) 
    {
      faceAnalyzerConfig->eyeDetectorCascadeFile = variableMap["eye_detector_cascade_file"].as<string>();
    }

  if (variableMap.count("face_thumbnail_path")) 
    {
      faceAnalyzerConfig->faceThumbnailOutputPath = variableMap["face_thumbnail_path"].as<string>();
    }
}
