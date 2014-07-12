#include "opencv2/highgui/highgui.hpp"
#include "opencv2/imgproc/imgproc.hpp"

#include <boost/lexical_cast.hpp>

#include <cmath>
#include <iostream>
#include <limits>
#include <string>


using namespace std;
using namespace cv;

static const char * usage = R"USAGE(
Usage: imagediff test1.jpg [test2.jpg]

When two images are provided as an argument, returns a number from 0-1
quantifying how different their color histograms are.

By definition images of different resolution are considered to have
difference = 1, to compare images of differing dimensions first scale
them to be the same size.

When one image is provided as an argument, returns a JSON string of
the RGB histogram formatted as:

{ "width"  : 123,
  "height" : 456, 
  "r_hist" : [ 0, 0, 19, 43, 1534, ... ],
  "g_hist" : [ 0, 0, 19, 43, 1534, ... ],
  "b_hist" : [ 0, 0, 19, 43, 1534, ... ] }

Each _hist array has 16 elements, and the value in the Nth position is
the number of pixels whose of the corresponding color whose upper four
bits in binary are N.

)USAGE";

// Return a JSON formatted string with the RGB histogram data.
void format_json( int width, int height, const Mat & bhist, const Mat & ghist, const Mat & rhist, string * result ) {
  // Just format the string manually - no need for a library here.
  *result += "{";
  *result += "\"width\":" + boost::lexical_cast<std::string>( width ) + ",";
  *result += "\"height\":" + boost::lexical_cast<std::string>( height ) + ",";

  *result += "\"r_hist\":[";
  for ( int i = 0 ; i < rhist.rows-1 ; i++ ) {
    *result += boost::lexical_cast<std::string>( rhist.at<float>( 0, i ) ) + ",";
  }
  *result += boost::lexical_cast<std::string>( rhist.at<float>( 0, rhist.rows-1 ) ) + "],";

  *result += "\"g_hist\":[";
  for ( int i = 0 ; i < ghist.rows-1 ; i++ ) {
    *result += boost::lexical_cast<std::string>( ghist.at<float>( 0, i ) ) + ",";
  }
  *result += boost::lexical_cast<std::string>( ghist.at<float>( 0, ghist.rows-1 ) ) + "],";

  *result += "\"b_hist\":[";
  for ( int i = 0 ; i < bhist.rows-1 ; i++ ) {
    *result += boost::lexical_cast<std::string>( bhist.at<float>( 0, i ) ) + ",";
  }
  *result += boost::lexical_cast<std::string>( bhist.at<float>( 0, bhist.rows-1 ) ) + "]";

  *result += "}";

  return;
}


/**
 * @function main
 */
int main( int argc, char** argv ) {
  Mat a, b, dst;
  
  if ( argc == 2 || argc == 3 ) {
    // Process the first image.
    a = imread( argv[1], CV_LOAD_IMAGE_COLOR );
    if( !a.data )
      { return -1; }
    
    /// Separate the image in 3 places ( B, G and R )
    vector<Mat> a_bgr_planes;
    split( a, a_bgr_planes );
    
    /// Establish the number of bins
    int histSize = 16;
    
    /// Set the ranges ( for B,G,R) )
    float range[] = { 0, 256 } ;
    const float* histRange = { range };
    
    bool uniform = true; bool accumulate = false;
    
    Mat a_b_hist, a_g_hist, a_r_hist;

    /// Compute the histograms:
    calcHist( &a_bgr_planes[0], 1, 0, Mat(), a_b_hist, 1, &histSize, &histRange, uniform, accumulate );
    calcHist( &a_bgr_planes[1], 1, 0, Mat(), a_g_hist, 1, &histSize, &histRange, uniform, accumulate );
    calcHist( &a_bgr_planes[2], 1, 0, Mat(), a_r_hist, 1, &histSize, &histRange, uniform, accumulate );

    // If we were called with only one argument, just print out the
    // histogram data and exit.
    if ( argc == 2 ) {
      string * result = new string();
      format_json( a.cols, a.rows, a_b_hist, a_g_hist, a_r_hist, result );
      cout << *result << endl;
      free( result );
      return 0;
    }
    
    // Otherwise compute the differenace and print the score.
    b = imread( argv[2], CV_LOAD_IMAGE_COLOR );
    if( !b.data )
      { return -1; }
    
    // If the images have different sizes, we assume they are different
    // for the purposes of this application.
    if ( a.size() != b.size() ) {
      cout << 1 << endl;
      return 0;
    }
    
    // Otherwise return the difference of their color histograms,
    // normalized from 0-1.
    vector<Mat> b_bgr_planes;
    split( b, b_bgr_planes );
    
    Mat b_b_hist, b_g_hist, b_r_hist;
    
    calcHist( &b_bgr_planes[0], 1, 0, Mat(), b_b_hist, 1, &histSize, &histRange, uniform, accumulate );
    calcHist( &b_bgr_planes[1], 1, 0, Mat(), b_g_hist, 1, &histSize, &histRange, uniform, accumulate );
    calcHist( &b_bgr_planes[2], 1, 0, Mat(), b_r_hist, 1, &histSize, &histRange, uniform, accumulate );
    
    double total_diff = 0;
    
    for( int i = 0; i < histSize; i++ ) {
      total_diff += abs( a_b_hist.at<float>(i) - b_b_hist.at<float>(i) )
	+ abs( a_g_hist.at<float>(i) - b_g_hist.at<float>(i) )
	+ abs( a_r_hist.at<float>(i) - b_r_hist.at<float>(i) );
    }
    
    cout << total_diff / ( 6 * a.rows * a.cols ) << endl;
    
    return 0;
  } else {
    cout << usage;
    return 0;
  }
}
