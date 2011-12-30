# drupdate v0.7.4a #

drupdate is a python script which allows for complete update to a [Drupal](http://www.drupal.org) installation on a remote server.  It can also perform a fresh install of the latest version of Drupal.  It was desiged to be used on shared hosts, where ssh access isn't allowed, but it should work for any setup.

## Quick Start ##

    git clone http://github.com/brcooley/drupdate.git drupdate
    cd drupdate
    python3 drupdate.py [user:pw@]host.com

## Status ##

drupdate now supports Windows and OS X!

Currently, the source is messy and full of debugging code.  _However_, minimal testing has been done, and multiple sites have been sucessfully updated.  Use at your own risk, and I would recommend running on a test server before you touch your production site.

#### Features ####

 + Automatically downloads and unpacks the latest version of Drupal.  Just specify the version number with -V or in the config file.  (Currently, drupdate will attempt to install Drupal 7.10 if no version is specified)
 + Supports `.netrc` files
 + Save any files or directories that reside in your Drupal root.  Just list them in the config file
 + Testrun to see what files drupdate plans on modifying before actually starting the operation.  Use -t when starting drupdate
 + Trying to connect to an old FTP server and having trouble?  Try setting `MLSDSupport` to false in the config file

#### Limitations ####

 + drupdate is designed with simplicity in mind.  Therefore, it does not do all of the recommended steps when updating Drupal, namely putting the site into maintainace mode and backing up the mySQL database.  Please complete these steps manually if they are important to you.
 + drupdate only uses one FTP connection.  This means it might seem slower than other FTP clients.  However, this also guarentees that drupdate will never open too many connections to your remote server, thus timing out (something other FTP clients _also_ do)

## Installation ##

Simply download the drupdate.py file along with .duConfig.conf and run it (Python 3.1.x or greater).  Drupdate should support Windows, OS X, and Linux assuming you have a full python installation.

## Planned Features ##

drupdate may not be quite as useful as some other [alternatives](http://drush.ws) currently, but hopefully it will be in the near future.  The goal of the project is a painless one step install/update script that does what the user expects it to do.  With this in mind, here are some of the features that are planned to be added.  If you actually find drupdate useful, but would like to see a feature not listed here, create an issue, and I'll look into adding it.  Alternatively, submit a pull request!  The return time on those is likely to be much shorter.

+ Automatically find the latest version of Drupal without prompting
+ Multiple FTP connections for faster updating.
+ Automatic MySQL backups for when things do go wrong
+ Session restoring, so that each run of drupdate doesn't have to update/install from scratch
