/*
	Filesystem related functions based mostly on boost's cross platorm libraries for file system related functionality

	Date: 20/6/2013

	Author: Jason Catchpole (jason@viblio.com)
*/

#pragma once

#include <map>


namespace FileSystem
{
  bool GetDirectoryContents(const std::string &directory, std::map<std::string,bool> &contents);

  bool FileExists(const std::string &filename);

  bool DirectoryExists(const std::string &path);

  bool CreateDirectory(const std::string &dir_name);
}
