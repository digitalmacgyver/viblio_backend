/*
*	Contains definitions of all the different types of video sources we can have
*
*	Date 3/7/2013
*
*	Author: Jason Catchpole
*/


#ifndef __VIDEOSOURCE_TYPES__
#define __VIDEOSOURCE_TYPES__

namespace VideoSource
{

enum VideoSourceTypes
{
	VideoSource_Webcam,
	VideoSource_File,
	VideoSource_Upload,
	VideoSource_Stream
};

} // end of namespace

#endif