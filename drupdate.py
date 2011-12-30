#! /usr/bin/python3
# -*- coding: utf-8 -*-

''' drupdate is a one-step drupal updater
	Copyright (C) 2011  Brett Cooley

	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>. '''

import logging as log
'''
	Logging level definitions:
	-- DEBUG: Debugging and system information/user input
	-- INFO: Status, ftp command info
	-- WARNING: Error which does not impede functionality
	-- ERROR: Major failure which allows program to run, but impedes functionality
	-- CRITICAL: Error causing program abort
'''

import sys
import re
import time
import ftplib
import json
import os
import shutil
import urllib.request
import tarfile
from getpass import *
from optparse import *
from netrc import *
from subprocess import *

LOG_FILE = time.strftime('.%Y-%m-%d.log')
CONFIG_FILE = '.drupdate.conf'
PROG_TITLE = 'drupdate'
VERSION = '0.7.4a'

DEF_CONFIG = {
		'DirectoriesToSave' : '',
		'FilesToSave' 		: '',
		'DrupalBaseDir' 	: 'public_html',
		'DrupalVersion' 	: '7.10',
		'MLSDSupport'		: 'True'
	}

ftpConn = None
verbose = True
testrun = False
i = j = 0
configDict = {}


def collectLogin(mainArg, userN='', pw='', acct=''):
	''' Collects host, username, password, and optional account information. '''
	log.debug(sys.platform)
	if sys.platform == 'linux2':
		try:
			ftpInfo = netrc()
			if ftpInfo.authenticators(remoteSrv) != None:
				userN, acct, pw = ftpInfo.authenticators(remoteSvr)
		except IOError:
			log.warning('No .netrc file found')

	if '@' in mainArg[0]:
		upBundle, remoteSvr = mainArg[0].split('@')
		if ':' in upBundle:
			userN, pw = upBundle.split(':')
		else:
			userN = upBundle
	else:
		remoteSvr = mainArg[0]

	if len(userN) == 0:
		userN = input('Username at {}: '.format(remoteSvr))

	if len(pw) == 0:
		try:
			pw = getpass()
		except GetPassWarning:
			log.warning('Password echo off failed')
			if input("WARNING! Password may be echoed, press 'y' to continue anyways: ").upper() == 'Y':
				pw = getpass()
			else:
				printAndLog('Echoed password input aborted by user, {} exiting'.format(PROG_TITLE), log.INFO, True)
				sys.exit(3)
	log.debug(userN)
	return (remoteSvr.strip(), userN.strip(), pw.strip(), acct.strip())


def deleteDir(rootDir):
	''' Recursive function which deletes entire directory trees. '''
	global ftpConn, j, testrun
	if testrun:
		global i
		i += 1
	curDirList = []
	ftpConn.cwd(rootDir)
	fList = ftpConn.nlst()
	fList.remove('.')
	fList.remove('..')
	if configDict['MLSDSupport']:
		dirFilter = mlsdFilter(curDirList)
		ftpConn.retrlines('MLSD', dirFilter)
	else:
		dirFilter = listFilter(curDirList)
		ftpConn.retrlines('LIST', dirFilter)

	for item in fList:
		if item in curDirList:
			deleteDir(item)
		else:
			if testrun == False:
				ftpConn.delete(item)
				if j % 4 == 3:
					sprint('\b\b| ', end='')
				elif j % 4 == 2:
					sprint('\b\b\\ ',end='')
				elif j % 4 == 1:
					sprint('\b\b- ', end='')
				else:
					sprint('\b\b/ ', end='')
				j += 1
				sys.stdout.flush()
			else:
				sprint('-'*i,end='')
				sprint('Deleting {}'.format(item))

	ftpConn.cwd('..')
	if testrun == False:
		ftpConn.rmd(rootDir)
	else:
		sprint('='*i,end='')
		sprint('Removing {}'.format(rootDir))
		i -= 1
	return


def uploadDir(rootDir):
	''' Recursive function which uploads entire directory trees. '''
	global ftpConn, j, testrun
	if testrun:
		global i
		i += 1
		sprint('='*i,end='')
		sprint('Creating {}'.format(rootDir))
	else:
		ftpConn.mkd(rootDir)
		ftpConn.cwd(rootDir)

	os.chdir(rootDir)
	fList = os.listdir(os.getcwd())
	for item in fList:
		if os.path.isdir(item):
			uploadDir(item)
		else:
			if testrun == False:
				try:
					openF = open(item,'rb')
				except IOError:
					printAndLog("\nCould not open {} to upload, skipping".format(item), log.ERROR, True)
				ftpConn.storbinary('STOR {}'.format(item),openF)
				if j % 4 == 3:
					sprint('\b\b| ', end='')
				elif j % 4 == 2:
					sprint('\b\b\\ ',end='')
				elif j % 4 == 1:
					sprint('\b\b- ', end='')
				else:
					sprint('\b\b/ ', end='')
				j += 1
				sys.stdout.flush()
			else:
				sprint('-'*i,end='')
				sprint('Uploading {}'.format(item))

	ftpConn.cwd('..')
	os.chdir('..')
	if testrun:
		i -= 1
	return


def mlsdFilter(localList):
	''' Callback function with closure for retrlines call that finds directories and appends them to the passed list. '''
	def findDir(fileInfo):
		if re.search(r'type=dir;',fileInfo):
			localList.append(fileInfo.split(';')[7].strip())
	return findDir


def listFilter(localList):
	''' Callback function with closure for retrlines call that finds directories and appends them to the passed list. '''
	def findDir(fileInfo):
		if re.match(r'^d',fileInfo) and fileInfo.split()[8].strip() not in ['.','..']:
			localList.append(fileInfo.split()[8].strip())
	return findDir


def cleanLogs(save):
	''' Removes old log files if there are more than 10 in the current directory. '''
	fileList = os.listdir(os.getcwd())
	logFiles = [x for x in fileList if re.match(r'^\..*\.log$',x) and x != LOG_FILE]
	if len(logFiles) > 9:
		if save:
			if not os.path.isdir('.logs'):
				os.mkdir('.logs')
			for logFile in logFiles:
				if os.path.isfile(os.path.join('.logs',logFile)):
					os.unlink(os.path.join('.logs',logFile))
				os.rename(logFile,os.path.join('.logs',logFile))
		else:
			for logFile in logFiles:
				os.unlink(logFile)


def main():
	global ftpConn, verbose, testrun, configDict
	#TODO fix logging to respect debug flag

	log.basicConfig(filename=LOG_FILE,level=log.INFO)
	log.info('---\nLogging started')
	try:
		configDict = json.load(open(CONFIG_FILE,'r'))
		log.info('Config file loaded')
	except IOError:
		printAndLog('Config file not found at {}, proceeding with default configuration'.format(CONFIG_FILE),log.ERROR,True)
		if input("WARNING: This may delete important files in the update process, press 'y' to continue: ").upper() == 'Y':
			configDict = DEF_CONFIG
		else:
			printAndLog('Unconfigured script aborted by user, {} exiting'.format(PROG_TITLE),log.INFO,True)
			sys.exit(4)

	''' Option -A currently does not work  '''
	parser = OptionParser(description=DESC, prog=PROG_TITLE, version='{} version {}'.format(PROG_TITLE, VERSION),
						usage='drupupdate.py [options] host')
	parser.add_option('-v','--ver', help="Specify the version of drupal to get, like 'X.y'", metavar='VER')
	parser.add_option('-u','--user', help='Specify a username to login to a host with')
	parser.add_option('-p','--password', help='Password to use with login', metavar='PASS')
	parser.add_option('--account', help='Specify an account to use with login', metavar='ACCT')
	parser.add_option('-k','--keep', action='store_true', default=False, help='Keeps both the local Drupal directory and the .tar')
	parser.add_option('-n','--no-get',action='store_true', default=False, help='Stops the script from downloading and unpacking Drupal')
	parser.add_option('-q','--quiet',action='store_true', default=False, help='Silences output')
	parser.add_option('-s','--save-logs',action='store_true', default=False,
						help='Tells drupdate move old logs to the .log folder instead of deleting them')
	parser.add_option('-t','--testrun', action='store_true', default=False,
					help="Same as a normal run, except files aren't actually changed.  A detailed log of operations is printed to stdout")
	#parser.add_option('-d','--debug', action='store_true', default=False,
	#				  help='Turns on debugging (WARNING: This will log private information, such as usernames)')
	#parser.add_option('-A','--auto', action='store_true',
	#				  help='Tells the updater to automatically find the latest version of Drupal')
	options, reqArgs = parser.parse_args()

	if len(reqArgs) < 1:
		parser.print_help()
		sys.exit(2)

	if options.quiet:
		verbose = False
	if options.testrun:
		testrun = True
	#if options.debug:
	#	log.basicConfig(filename=LOG_FILE,level=log.DEBUG)
	#	log.debug('Debugging on')
	if options.ver != None:
		drupalVer = options.ver.split('.')
	else:
		drupalVer = configDict['DrupalVersion'].split('.')

	if options.no_get == False:

		### STATUS
		printAndLog('Starting download of Drupal {0[0]}.{0[1]}'.format(drupalVer),log.INFO)
		###

		downloadInfo = urllib.request.urlretrieve(
						'http://drupal.org/files/projects/drupal-{0[0]}.{0[1]}.tar.gz'.format(drupalVer),
						os.path.join(os.getcwd(),'drupal-{0[0]}.{0[1]}.tar.gz'.format(drupalVer)))

		### STATUS
		printAndLog('Download finished, unpacking...',log.INFO)
		###

		tar = tarfile.open('drupal-{0[0]}.{0[1]}.tar.gz'.format(drupalVer))
		tar.extractall()
		tar.close()

	passUser = passPass = passAcct = ''

	if options.user != None:
		passUser = options.user
	if options.password != None:
		passPass = options.password
	if options.account != None:
		passAcct = options.account

	remoteSvr, userN, pw, acct = collectLogin(reqArgs,passUser,passPass,passAcct)

	ftpConn = ftplib.FTP()
	try:
		ftpConn.connect(remoteSvr)
		log.info('Connection made to {}'.format(remoteSvr))
		ftpConn.login(userN,pw,acct)
	except ftplib.all_errors:		# TODO break out, create fixes for each error
		printAndLog('Something went wrong...',log.CRITICAL,True,sys.stderr)
		sys.exit(1)

	ftpConn.cwd(configDict['DrupalBaseDir'])
	log.debug('Current dir: {}'.format(ftpConn.pwd()))
	curFileList = [x for x in ftpConn.nlst() if x not in ['.','..']]

	dirList = []
	if configDict['MLSDSupport']:
		dirFilter = mlsdFilter(dirList)
		ftpConn.retrlines('MLSD',dirFilter)
	else:
		dirFilter = listFilter(dirList)
		ftpConn.retrlines('LIST',dirFilter)
	log.debug('Current dir listing:\n{}'.format(curFileList))
	curWD = ftpConn.pwd()

	### STATUS
	sprint('Removing files --   ',end='')
	sys.stdout.flush()
	###

	for item in curFileList:
		if item not in configDict['DirectoriesToSave'] and item not in configDict['FilesToSave']:
			if item in dirList:
				deleteDir(item)
			else:
				if testrun == False:
					ftpConn.delete(item)
				else:
					sprint('Deleting {}'.format(item))
	sprint('')

	### STATUS
	printAndLog("Removal complete, starting upload",log.INFO)
	###

	try:
		os.chdir('drupal-{0[0]}.{0[1]}'.format(drupalVer))
	except OSError:
		printAndLog("Drupal directory not found, exiting",log.CRITICAL,True,sys.stderr)
		sys.exit(1)

	### STATUS
	sprint("Uploading files --   ",end='')
	###

	for item in os.listdir(os.getcwd()):
		if item not in configDict['DirectoriesToSave'] and item not in configDict['FilesToSave']:
			if os.path.isdir(item):
				uploadDir(item)
			else:
				if testrun == False:
					openF = open(item,'rb')
					log.debug('Storing {}'.format(item))
					ftpConn.storbinary('STOR {}'.format(item),openF)
				else:
					sprint('Uploading {}'.format(item))
	sprint('')

	### STATUS
	sprint('Drupal successfully updated to {0[0]}.{0[1]}'.format(drupalVer))
	###

	if options.keep == False:
		os.chdir('..')
		shutil.rmtree('drupal-{0[0]}.{0[1]}'.format(drupalVer),True)
		os.unlink('drupal-{0[0]}.{0[1]}.tar.gz'.format(drupalVer))

	try:
		ftpConn.quit()
	except ftplib.all_errors:
		ftpConn.close()
	log.info('Connection to {} closed'.format(remoteSvr))
	log.shutdown()
	cleanLogs(options.save_logs)


def printAndLog(message, level=log.DEBUG, verbOverride=False, printStream=sys.stdout):
	''' A simple method which prints and logs the same message. '''
	log.log(level, message)
	if verbose or verbOverride:
		print(message, file=printStream)


def sprint(message,sep=' ',end='\n',file=sys.stdout):
	''' Simple wrapper to print method that respects verbose option. '''
	if verbose:
		print(message,sep=sep,end=end,file=file)


DESC = '''
	A simple python script which automatically removes and replaces a 'typical' Drupal install on a
remote FTP server.  Only tested on Drupal 7.x installs, use with care
'''

if __name__ == '__main__':
	main()
