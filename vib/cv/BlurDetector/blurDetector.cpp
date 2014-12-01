#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include "opencv2/imgproc/imgproc.hpp"
#include "opencv2/opencv.hpp"
#include <iostream>
#include <limits>
#include <math.h>
#include <numeric>
#include <unistd.h>
#include <string>
using namespace cv;
using namespace std;

// The paper that is used in this implementation is -
/*  No-reference Perceptual Blur Metric
Pina Marziliano, Frederic Dufaux, Stefan Winkler and Touradj Ebrahimi
IEEE 2002 International Conference on Image Processing
*/

// OpenCV Matricies are defined in terms of rows, and them columns.  
//
// The first parameter in at is the row value (e.g. the y coordinate)
//
// The second parameter is the column value (e.g. the x coordinate)
//
// In matrix calculations, the Mij element in the i'th row and the
// j'th column (measured from the top left).

// Arguments:
// edges - a grayscale Mat where edges are indicated with white (255)
//         values - must have the same dimensions as the source image.
// original - the source image
// vblur, hblur - optional output parameters, if defined the vertical
//                blur / horizontabl blur will be calculated and stored
// vert_edges, hor_edges - optional output paramters, if defined
//         assumed to have the same dimensions as the original image.
//         If present a black and white image vizualizing the detected
//         edge widths will be returned.
// monotonic - optional, if true edge width calculation requires
//         monotonic increasing changes (if false edges are extended
//         over regions that have the same value)
// truncate_extrema_edges - When the edge point is itself an extrema,
//         if the value is true the edge width is 2, otherwise the
//         edge is calculated in the usual way (extending out until a
//         (non)-monotonic point is found).
// only_transitions - When true we only calculate things if we are at
//         a white pixel, and the prior pixel is black.
// debug - optional
void getBlurValue2( const Mat &edges, const Mat &original, 
		    double * vblur, double * hblur, 
		    Mat * vert_edges = NULL, Mat * hor_edges = NULL, 
		    bool monotonic=true, bool truncate_extrema_edges=true, bool only_transitions=false, 
		    bool debug=false  ) {
  int num_vert_edges = 0;
  double vert_total = 0;
  int num_hor_edges = 0;
  double hor_total = 0;

  for ( int i = 1 ; i < original.rows - 1 ; i++ ) {
    for ( int j = 1 ; j < original.cols - 1 ; j++ ) {
      if ( debug ) {
	cout << "i: " << i << " j: " << j << " edges: " << int( edges.at<unsigned char>( i, j ) ) << endl;
      }

      int x = int( edges.at<unsigned char>( i, j ) );
      if ( x != 0 && x != 255 ) {
	cout << "ERROR: x of " << x << " for i, j " << i << ", " << j << endl;
      }

      // Compute blur on vertical edges
      //
      // The blur on vertical edges is found by considering the
      // horizontal width of the edges, so by exploring the regions in
      // adjacent columns of the initial value, as indexed by the
      // second parameter to at.
      if ( vblur && int( edges.at<unsigned char>( i, j ) ) == 255 && 
	   ( !only_transitions || int( edges.at<unsigned char>( i, j-1 ) ) == 0 ) )  {
	// With Canny edge detection our edges are generally of width
	// one - if some other edge detector is used that gives rise
	// to wider edges we may wish to enforce that we only do the
	// edge calculation on the transition from black to white.

	// A vertical line has started here
	int left = j - 1;
	int current = j;
	int right = j + 1;
	int left_value = original.at<unsigned char>( i, left );
	int current_value = original.at<unsigned char>( i, current );
	int right_value = original.at<unsigned char>( i, right );

	if ( vert_edges ) {
	  vert_edges->at<unsigned char>( i, current ) = 255;
	}

	// Walk backwards till we obtain a local extrema to the left.
	for ( int prior_value = current_value; 
	      left > 0 && // While we're still in the image.
		( ( ( left_value < prior_value && left_value < current_value ) 
		    || ( !monotonic && left_value <= prior_value && left_value <= current_value ) ) || // And decreasing
		  ( ( left_value > prior_value && left_value > current_value ) 
		    || ( !monotonic && left_value >= prior_value && left_value >= current_value ) ) ) ; // Or increasing
	      left--, prior_value = left_value, left_value = original.at<unsigned char>( i, left ) ) {
	  if ( vert_edges && left >= 0 ) {
	    vert_edges->at<unsigned char>( i, left ) = 255;
	  }
	}
	// Now left is one past the position of the local extrema to
	// the left - or the edge of the image.
	left++;
	left_value = original.at<unsigned char>( i, left );

	// Walk forwards till we obtain a local extrema to the right.
	for ( int prior_value = current_value; 
	      right < original.cols && // While we're still in the image.
		( ( ( right_value < prior_value && right_value < current_value ) 
		    || ( !monotonic && right_value <= prior_value && right_value <= current_value ) ) || // And decreasing
		  ( ( right_value > prior_value && right_value > current_value ) 
		    || ( !monotonic && right_value >= prior_value && right_value >= current_value ) ) ) ; // Or increasing
	      right++, prior_value = right_value, right_value = original.at<unsigned char>( i, right ) ) {
	  if ( vert_edges && right < original.cols ) {
	    vert_edges->at<unsigned char>( i, right ) = 255;
	  }
	}
	// Now right is one past the position of the local extrema to
	// the left - or the edge of the image.
	right--;
	right_value = original.at<unsigned char>( i, right );

	if ( ( left_value > current_value && right_value > current_value ) ||
	     ( left_value < current_value && right_value < current_value ) ) {
	  // Corner case - the edge location itself was itself is a
	  // local extrema.
	  if ( truncate_extrema_edges ) {
	    vert_total += 2;
	    num_vert_edges++;
	  } else {
	    if ( debug ) {
	      cout << "EXTREMA:  " << "i: " << i << " l-c-r: " << left << "-" << current << "-" << right << " lv-pv-cv-nv-rv " << left_value << "-" << int( original.at<unsigned char>( i, j-1 ) ) << "-" << current_value << "-" << int( original.at<unsigned char>( i, j+1 ) ) << "-" << right_value << endl;
	    }
	    if ( abs( left_value - current_value ) > abs( right_value - current_value ) ) {
	      vert_total += current - left;
	      num_vert_edges++;
	    } else if ( abs( left_value - current_value ) < abs( right_value - current_value ) ) {
	      vert_total += right - current;
	      num_vert_edges++;
	    } else {
	      // Super duper corner case - the edge is a local extrema
	      // and both left and right are candidates for the other
	      // extrema - split the difference.
	      vert_total += ( right - left ) / 2;
	      num_vert_edges++;
	    }
	  }
	} else {
	  if ( debug ) {
	    cout << "STANDARD: " << "i: " << i << " l-c-r: " << left << "-" << current << "-" << right << " lv-pv-cv-nv-rv " << left_value << "-" << int( original.at<unsigned char>( i, j-1 ) ) << "-" << current_value << "-" << int( original.at<unsigned char>( i, j+1 ) ) << "-" << right_value << endl;
	  }
	  vert_total += right - left;
	  num_vert_edges++;
	}
      }

      // Compute blur on horizontal edges
      if ( hblur && int( edges.at<unsigned char>( i, j ) ) == 255 && 
	   ( !only_transitions || int( edges.at<unsigned char>( i-1, j ) ) == 0 ) ) {

	// A vertical line has started here
	int up = i - 1;
	int current = i;
	int down = i + 1;
	int up_value = original.at<unsigned char>( up, j );
	int current_value = original.at<unsigned char>( current, j);
	int down_value = original.at<unsigned char>( down, j );

	if ( hor_edges ) {
	  hor_edges->at<unsigned char>( current, j ) = 255;
	}

	// Walk backwards till we obtain a local extrema above.
	for ( int prior_value = current_value; 
	      up > 0 && // While we're still in the image.
		( ( ( up_value < prior_value && up_value < current_value ) 
		    || ( !monotonic && up_value <= prior_value && up_value <= current_value ) ) || // And decreasing
		  ( ( up_value > prior_value && up_value > current_value ) 
		    || ( !monotonic && up_value >= prior_value && up_value >= current_value ) ) ) ; // Or increasing
	      up--, prior_value = up_value, up_value = original.at<unsigned char>( up, j ) ) {
	  if ( hor_edges && up >= 0 ) {
	    hor_edges->at<unsigned char>( up, j ) = 255;
	  }
	}
	// Now up is one past the position of the local extrema above
	// - or the edge of the image.
	up++;
	up_value = original.at<unsigned char>( up, j );

	// Walk forwards till we obtain a local extrema below.
	for ( int prior_value = current_value; 
	      down < original.rows && // While we're still in the image.
		( ( ( down_value < prior_value && down_value < current_value ) 
		    || ( !monotonic && down_value <= prior_value && down_value <= current_value ) ) || // And decreasing
		  ( ( down_value > prior_value && down_value > current_value ) 
		    || ( !monotonic && down_value >= prior_value && down_value >= current_value ) ) ) ; // Or increasing
	      down++, prior_value = down_value, down_value = original.at<unsigned char>( down, j ) ) {
	  if ( hor_edges && down < original.rows ) {
	    hor_edges->at<unsigned char>( down, j ) = 255;
	  }
	}
	// Now down is one past the position of the local extrema
	// below - or the edge of the image.
	down--;
	down_value = original.at<unsigned char>( down, j );

	if ( ( up_value > current_value && down_value > current_value ) ||
	     ( up_value < current_value && down_value < current_value ) ) {
	  // Corner case - the edge location itself was itself is a
	  // local extrema.
	  if ( truncate_extrema_edges ) {
	    hor_total += 2;
	    num_hor_edges++;
	  } else {
	    if ( debug ) {
	      cout << "EXTREMA:  " << "j: " << j << " l-c-r: " << up << "-" << current << "-" << down << " uv-pv-cv-nv-dv " << up_value << "-" << int( original.at<unsigned char>( i-1, j ) ) << "-" << current_value << "-" << int( original.at<unsigned char>( i+1, j ) ) << "-" << down_value << endl;
	    }
	    if ( abs( up_value - current_value ) > abs( down_value - current_value ) ) {
	      hor_total += current - up;
	      num_hor_edges++;
	    } else if ( abs( up_value - current_value ) < abs( down_value - current_value ) ) {
	      hor_total += down - current;
	      num_hor_edges++;
	    } else {
	      // Super duper corner case - the edge is a local extrema
	      // and both up and down are candidates for the other
	      // extrema - split the difference.
	      hor_total += ( down - up ) / 2;
	      num_hor_edges++;
	    }
	  }
	} else {
	  if ( debug ) {
	    cout << "STANDARD: " << "j: " << j << " l-c-r: " << up << "-" << current << "-" << down << " uv-pv-cv-nv-dv " << up_value << "-" << int( original.at<unsigned char>( i-1, j ) ) << "-" << current_value << "-" << int( original.at<unsigned char>( i+1, j ) ) << "-" << down_value << endl;
	  }
	  hor_total += down - up;
	  num_hor_edges++;
	}
      }
    }
  }

  if ( vblur ) {
    if ( num_vert_edges ) {
      *vblur = vert_total / num_vert_edges;
    } else {
      *vblur = 0;
    }
  }
  if ( hblur ) {
    if ( num_hor_edges ) {
      *hblur = hor_total / num_hor_edges;
    } else {
      *hblur = 0;
    }
  }
  return;
}

#define CANNY_THRESH_MEAN 0
#define CANNY_THRESH_OTSU 1

// Compute the Canny edge detection for src, save the result in canny.
// If debug is true outfile_prefix must be defined.
void get_canny_edges( const Mat * src, Mat * canny, int bw_threshold=CANNY_THRESH_OTSU, bool debug=false, const string * outfile_prefix = NULL ) {
  Mat src_gray, blurred_gray;
  // Convert the input image to grayscale.
  cvtColor( *src, src_gray, CV_BGR2GRAY );

  if ( debug ) {
    imwrite( *outfile_prefix + "_gray.jpg", src_gray );
  }

  // For Canny edge detection, some implementations recommend blurring
  // the image first to reduce / eliminate noise.
  //
  //blur( src_gray, blurred_gray, Size( 3, 3 ) );
  blurred_gray = src_gray;

  // Compute the canny threshold, try the mean value of the grayscale
  // image.
  Mat unused;
  int high, low;
  if ( bw_threshold == CANNY_THRESH_OTSU ) {
    high = threshold( blurred_gray, unused, 0, 255, THRESH_BINARY + THRESH_OTSU )*.4;
    low = 0.5 * high;
  } else {
    double gray_mean = mean( src_gray )[0];
    high = 1.33*gray_mean;
    low = .66*gray_mean;
  }

  if ( debug ) {
    cout << "Canny low, high is: " << low << ", " << high << endl;
  }

  // The threshold value of 20 was selected after some ad-hoc testing.
  Canny( blurred_gray, *canny, low, high, 3 );
  
  if ( debug ) {
    imwrite( *outfile_prefix + "_canny.jpg", *canny );
  }
}

// Compute Sobel in the x and y direction.
// If sobel_x or sobel_y are NULL those directions are not computed.
// If debug is true outfile_prefix must be defined.
void sobel_helper( const Mat & gradient, Mat * sobel, bool, const string *);
void get_sobel_edges( const Mat & src, Mat * sobel_x, Mat * sobel_y, bool debug=false, const string * outfile_prefix = NULL ) {
  Mat src_color, sobel_gradient_x, sobel_gradient_y;
  int scale = 1;
  int delta = 0;
  int ddepth = CV_16S;

  vector<Mat> Ycrcb;

  // Get a seperate luminance component to operate the edge width
  // algorithm on.
  cvtColor( src, src_color, CV_BGR2YCrCb );
  split( src_color, Ycrcb );
  
  if ( debug ) {
    imwrite( *outfile_prefix + "_Y.jpg", Ycrcb[0] );
  }

  if ( sobel_x ) {
    // Take sobel gradient on the luminance channel of the image
    Sobel( Ycrcb[0], sobel_gradient_x, ddepth, 1, 0, 3, scale, delta, BORDER_DEFAULT );
  
    if ( debug ) {
      imwrite( *outfile_prefix + "_sobel_x.jpg", sobel_gradient_x );
    }
    sobel_helper( sobel_gradient_x, sobel_x, debug, outfile_prefix );
  }
  if ( sobel_y ) {
    Sobel( Ycrcb[0], sobel_gradient_y, ddepth, 0, 1, 3, scale, delta, BORDER_DEFAULT );

    if ( debug ) {
      imwrite( *outfile_prefix + "_sobel_y.jpg", sobel_gradient_y );
    }
    sobel_helper( sobel_gradient_y, sobel_y, debug, outfile_prefix );
  }
}

// Given a sobel gradient turns it into a thresholded black and white image.
void sobel_helper( const Mat & gradient, Mat * sobel, bool debug=false, const string * outfile_prefix = NULL ) {
  Mat abs_grad;

  // Black to white edges have a positive slope, white to black a
  // negative slope.  We only care about the transition, not the
  // direction, so we need to take the absolute value of
  // sobel_gradient before proceeding.
  convertScaleAbs( gradient, abs_grad );
  
  if ( debug ) {
    imwrite( *outfile_prefix + "_abs_grad.jpg", abs_grad );  
  }

  double sobmin, sobmax;
  cv::minMaxLoc( abs_grad, &sobmin, &sobmax );

  if ( debug ) {
    cout << "Max: " << sobmax << "\nMin: " << sobmin << endl;
  }

  // Convert our image to a grayscale image scaled such that the
  // brightest spots are white and the darkest spots are black.
  cv::Mat sobelImage, unused;
  if ( sobmax != sobmin ) {
    abs_grad.convertTo( sobelImage,
			CV_8U, 255.0 / ( sobmax - sobmin ), // Scale
			-sobmin * 255.0 / ( sobmax - sobmin ) ); // Add after scaling
  } else {
    // Handle the case where the input image is a uniform color - just
    // turn the whole thing black.
    abs_grad.convertTo( sobelImage,
			CV_8U, 0, // Scale
			0 ); // Add after scaling
  }
  
  if ( debug ) {
    imwrite( *outfile_prefix + "_abs_grad_normalized.jpg", sobelImage );  
  }
  
  int bw_threshold = threshold( sobelImage, unused, 0, 255, THRESH_BINARY + THRESH_OTSU );

  if ( debug ) {
    cout << "Threshold: " << bw_threshold << endl;
  }

  // Turn it in to a black and white image where anything less than
  // our threshold is black, and anything more is white.
  cv::Mat sobelThresholdedImage;
  cv::threshold( sobelImage, *sobel, bw_threshold, 255, cv::THRESH_BINARY);
  
  if ( debug ) {
    imwrite( *outfile_prefix + "_abs_grad_thresholded.jpg", *sobel );  
  }
}

int main( int argc, char** argv ) {
  if( argc < 2) {
    cout <<" Usage: blurDetector image.png [debug_output_file_prefix]" << endl;
    return -1;
  }

  Mat src, image;

  src = imread( argv[1] );

  vector<Mat> Ycrcbchannels;

  // Get a seperate luminance component to operate the edge width
  // algorithm on.
  cvtColor( src, image, CV_BGR2YCrCb );
  split( image, Ycrcbchannels );
  
  bool debug = false;
  string * outfile_prefix = NULL;
  if ( argc == 3 ) {
    debug = true;
    outfile_prefix = new string( argv[2] );
  } else {
    outfile_prefix = new string( "blur-debug" );
  }

  // We can run through a variety of scenarios here with regard to the
  // optional parameters for getBlur.
  bool tests[8][3] = { { 0, 0, 0},
		       { 0, 0, 1},
		       { 0, 1, 0},
		       { 0, 1, 1},
		       { 1, 0, 0},
		       { 1, 0, 1},
		       { 1, 1, 0},
		       { 1, 1, 1} };
  const char * test_labels[] = { "m0-t0-r0",
				 "m0-t0-r1",
				 "m0-t1-r0",
				 "m0-t1-r1",
				 "m1-t0-r0",
				 "m1-t0-r1",
				 "m1-t1-r0",
				 "m1-t1-r1" };

  double vblur, hblur;
  Mat vert_edges;
  Mat hor_edges;

  Mat * de = new Mat();

  get_sobel_edges( src, de, NULL, debug, outfile_prefix );

  // We only run the m1-t1-r1 version of get blur for now.
  for ( int i = 7 ; i < 8 ; i++ ) {
    if ( debug ) {
      vert_edges = Mat::zeros( de->size(), de->type() );
      hor_edges = Mat::zeros( de->size(), de->type() ); 
      getBlurValue2( *de, Ycrcbchannels[0], &vblur, &hblur, &vert_edges, &hor_edges, tests[i][0], tests[i][1], tests[i][2], debug );
      imwrite( *outfile_prefix + "_sobel" + "_vert_edges_" + string( test_labels[i] ) + ".jpg", vert_edges );  
      imwrite( *outfile_prefix + "_sobel" + "_hor_edges_" + string( test_labels[i] ) + ".jpg", hor_edges );  
    } else {
      // Calculate the vertical blur only in normal usage.
      getBlurValue2( *de, Ycrcbchannels[0], &vblur, 0, 0, 0, tests[i][0], tests[i][1], tests[i][2], debug );
    }

    // Normalize to width of image - this gives a value between 0 and 100.
    cout << vblur * 100 / Ycrcbchannels[0].cols << endl;
  }

  free( outfile_prefix );
  return 0;
}

