/*
*	Contains definitions of all the different types of analyzer we can have and useful functions for handling these types etc
*
*	Date 3/7/2013
*
*	Author: Jason Catchpole
*/


#ifndef __ANALYZER_TYPES__
#define __ANALYZER_TYPES__

#include <string>
#include <algorithm>

namespace Analytics
{

enum AnalyzerType
{
	Analyzer_FaceAnalysis,
	UnknownAnalyzer
};

// takes a string which describes the analyzer and returns the corresonding type. Returns "UnknownAnalyzer"
// if it doesn't know what the string is
AnalyzerType ConvertStringToAnalyzerType(const std::string &analyzerStr)
{
	std::string lowerCaseVersion = analyzerStr;
	std::transform(lowerCaseVersion.begin(), lowerCaseVersion.end(), lowerCaseVersion.begin(), ::tolower);

	if( lowerCaseVersion.compare("faceanalysis") == 0 )
		return Analyzer_FaceAnalysis;
	else
		return UnknownAnalyzer;
}

} // end of namespace

#endif