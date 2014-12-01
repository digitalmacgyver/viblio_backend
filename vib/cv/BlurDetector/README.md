This code outputs a blur metric when an image is passed to it. Usually higher the blur metric value,  higher the blur in the image.

1. Make sure opencv is installed and run the following command.  

    ```
    $g++ -o blurDetector blurDetector.cpp `pkg-config opencv --cflags --libs`
    
    ```

2. It generates a binary called "blurDetector".  Pass any image to the binary to get a blur metric value. In the following program the blur metric value is stored in out.txt

     ```
      $ ./blurDetector test1.jpg
     ```
     
Note : During the primitive experimentation a value less than 4.0 means a sharp image and a higher value means a blurred image.  The best method would be to collect some blurry and sharp images from the kind of images we would see , plot their blur metric values and then decide a threshold. 

3. To view debug information for the blur detection, add a third
parameter which will prefix the various debugging output files:

     ```
      $ ./blurDetector test1.jpg test-debug-data
     ```

4. To build a debug version of the binary for use with GDB:

    ```
    $g++ -g -o blurDetector blurDetector.cpp `pkg-config opencv --cflags --libs`
    
    ```
    