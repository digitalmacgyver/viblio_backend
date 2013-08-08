/*
	Manages all the trackers that are currently active. When the process function is called
	it updates all the trackers so they can update their position. Also allows the caller to
	determine whether a recently detected face (or object) is already being tracked or not

	Date: 07/07/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#include "TrackingController.h"
#include "Tracker_OpenTLD.h"
#include "Face.h"

using namespace cv;


namespace Analytics
{
  namespace FaceAnalyzer
  {

    TrackingController::TrackingController(FaceAnalyzerConfiguration *faceAnalyzerConfiguration)
    {
      m_backgroundLearningTLD = new Tracker_OpenTLD();
      faceAnalyzerConfig = faceAnalyzerConfiguration;
    }

    TrackingController::~TrackingController()
    {
      if( m_backgroundLearningTLD != NULL )
	delete m_backgroundLearningTLD;

      // go through each of the trackers and destroy them
      for(auto startIter=m_trackedFaces.begin(); startIter != m_trackedFaces.end(); ++startIter)
	delete *startIter;

      m_trackedFaces.clear();

    }

    /*
      Determines whether the potentially new object/face whose position is specified in newObjectLocation
      is a new object or one that is already being tracked
    */
    bool TrackingController::IsAlreadyBeingTracked(const Rect &newObjectLocation)
    {
      if( m_trackedFaces.size() == 0 )
	return false;

      // not yet implemented. Currently always assumes there should only be 1 track thus if we are tracking
      // something the the new object is simply this same object that we are tracking already.
      //Eventually this will go through each of the trackers in m_trackers and determine if the newObjectLocation
      //is the same as any of the given trackers (by examining the overlap of the trackers estimated location
      //and the new objects location

      return true;
    }

    /*
      Adds a new tracker which is initialised using the provided object/face location that was detected
      in the provided frame
    */
    void TrackingController::AddNewTrack(const Mat &frame, Rect &objectLocation)
    {
      // It is possible that the new track is one we had previously, we should examine this
      // possibility here depending on the tracker and how discriminative it is (can it tell
      // that this new object is the one it was tracking previously). Alternatively, we could
      // use the face recognition module to help us determine this (assuming we had enough images
      // of the person we were tracking previously to be able to recognize them again in this
      // 'new' detection). Lastly we could simply consider every person new and try and consolidate
      // the people we are detected and tracked at the end of the processing (the problem with this
      // approach is we might only have a few thumbnails of each person to work with. Probably best
      // to do both, do it now (while tracking) while we have the maximum amount of source material 
      // to try and consolidate them, and again later just to be doubly sure

      // for the moment we'll just add a new tracker for this person
      //Tracker_OpenTLD *newTracker = new Tracker_OpenTLD();

      //m_backgroundLearningTLD->InitialiseTrack(frame, objectLocation);

      m_trackedFaces.push_back( new Face(m_backgroundLearningTLD, frame, objectLocation,faceAnalyzerConfig) );

      m_backgroundLearningTLD = NULL; // this ensures in the future we don't bother processing this tracker which was purely intended for learning the background
    }

    /*
      Updates each of the trackers that are active so that they can estimate the new position of
      the object/face they are tracking
    */
    void TrackingController::Process(const Mat &frame, uint64_t frameTimestamp)
    {
      if( m_backgroundLearningTLD != NULL )
	m_backgroundLearningTLD->Process(frame); // allow it to learn the background

      // could call each of these trackers in parallel assuming they are independent (they should 
      // be at least when they are estimating the new position of the object/face)
      for( auto startIter=m_trackedFaces.begin(); startIter!=m_trackedFaces.end(); ++startIter)
	{
	  (*startIter)->Process( frame, frameTimestamp );
	}
    }

    // end of namespaces
  }
}
