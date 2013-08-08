/*
	Filesystem related functions based mostly on boost's cross platorm libraries for file system related functionality

	Date: 20/6/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#include "boost/filesystem.hpp"
#include <string>
#include "FileSystem.h"

using namespace std;
using namespace boost::filesystem;


namespace FileSystem
{
  /*
    Returns true if it successfully obtained the contents of the dir. The contents returned
    has the name of the file/dir and a bool indicating if the entry was a directory (bool is true)
    or a file
  */
  bool GetDirectoryContents(const string &directory, map<string,bool> &contents)
  {
    path dir(directory);

    // first make sure this directory actually exists and that it indeed is a directory
    if(!exists(dir) || !is_directory(dir))
      return false;
    
    
    path file;
    
    directory_iterator end;
    for(directory_iterator itr(dir); itr != end; itr++)
      {
        file = itr->path();
        if(is_directory(file))
	  contents[file.string()] = true;
        else
	  contents[file.string()] = false;
      }

    return true;
  }

  bool FileExists(const string &filename)
  {
    return exists( filename ) && !is_directory(filename);
  }

  bool DirectoryExists(const string &path)
  {
    return exists( path ) && is_directory(path);
  }


  bool CreateDirectory(const string &dir_name)
  { 
    path dir(dir_name);
    if(create_directory(dir)) {
      cout <<" Created Directory at path: " << current_path().string() << endl;
      return true;
    }
    else
      {
	return false;
      }
  }


} // end of filesystem
