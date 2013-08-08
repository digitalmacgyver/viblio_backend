/*
	The entry point into the application. Parses command line options (or config files) and sets up the program
	flow based on said options

	Date: 01/07/2013

	Author: Jason Catchpole (jason@viblio.com)

*/

#include "FaceAnalyzer.h"
#include "FaceAnalyzerConfiguration.h"
#include "TrackingController.h"
#include "FileSystem/FileSystem.h"

#include <opencv2/opencv.hpp>
#include <stdexcept>

using namespace std;
using namespace cv;


namespace Analytics
{
  namespace FaceAnalyzer
  {


    // pass in some config information or have a global configuration settings object
    FaceAnalysis::FaceAnalysis(FaceAnalyzerConfiguration *faceAnalyzerConfig)
    {
      if( faceAnalyzerConfig == NULL )
	throw runtime_error("Face analyzer config was NULL");

      if( !faceAnalyzerConfig->faceThumbnailOutputPath.empty() )
	{
	  // if they specified an output path for thumbnails then make sure it exists, if it doesn't
	  // its an error so we will throw an exception (perhaps in future we could create the path?)
	  if( !FileSystem::DirectoryExists(faceAnalyzerConfig->faceThumbnailOutputPath) )
	    throw runtime_error("Specified output thumbnail directory does not exist");
	}

      m_faceDetector.reset( new FaceDetector_OpenCV(faceAnalyzerConfig->faceDetectorCascadeFile, faceAnalyzerConfig->eyeDetectorCascadeFile) );

      m_trackingController.reset( new TrackingController(faceAnalyzerConfig) );
    }


    FaceAnalysis::~FaceAnalysis()
    {

    }

    void FaceAnalysis::Process(const Mat &frame, uint64_t frameTimestamp)
    {

      // do 2 things in parallel here
      // 1. Perform face detection
      vector<Rect> detectedFaces = m_faceDetector->Detect( frame );

      // 2. Pass the frame off to the tracking controller to update any active trackers
      m_trackingController->Process(frame, frameTimestamp);

      // Now examine any detected faces to determine if they are new faces or ones that are already being tracked (the tracking controller can tell you if they are new or not)
      if( detectedFaces.size() > 0 )
	{
	  // iterate over all the new detections for this frame
	  for( auto startIter=detectedFaces.begin(); startIter!=detectedFaces.end(); ++startIter)
	    {
	      // determine if we have detected a new object to track or an existing one we are already tracking
	      if( !m_trackingController->IsAlreadyBeingTracked(*startIter) )
		{
		  // we've found a new object, better start tracking it
		  m_trackingController->AddNewTrack(frame, *startIter);
		}
	      // else do nothing as we are already tracking this one
	    }
	}

    }

    // end of namespaces
  }
}
