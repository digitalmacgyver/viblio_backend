Processes one or two images.

When two images are provided as an argument, returns a number from 0-1
quantifying how different their color histograms are.

By definition images of different resolution are considered to have
difference = 1, to compare images of differing dimensions first scale
them to be the same size.

When one image is provided as an argument, returns a JSON string of
the RGB histogram formatted as:

{ 'width'  : 123,
  'height' : 456, 
  'r_hist' : [ 0, 0, 19, 43, 1534, ... ],
  'g_hist' : [ 0, 0, 19, 43, 1534, ... ],
  'b_hist' : [ 0, 0, 19, 43, 1534, ... ] }

Each _hist array has 16 elements, and the value in the Nth position is
the number of pixels whose of the corresponding color whose upper four
bits in binary are N.

To build:
    ```
    $g++ -std=c++0x -o imagediff imagediff.cpp `pkg-config opencv --cflags --libs`
    
    ```

To run:
     ```
      $ ./imagediff test1.jpg
      or
      $ ./imagediff test1.jpg test2.jpg
     ```
     
