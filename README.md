Currently, the source is messy, full of debugging code, and untested.  _However_, editing the PROD variable to True should allow for the script
to be run, and in theory work.  I wouldn't try it on anything except a test server, however.

# drupdate

drupdate is a python script which allows for complete update to a [Drupal](http://www.drupal.org) installation on a remote server.
It was desiged to be used on shared hosts, where ssh access isn't allowed, but it should work for any setup.

## Installation

Simply download the drupdate.py file and run it (Python 3).
