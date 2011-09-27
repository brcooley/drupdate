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
	-- WARNING: Error which does not impeed functionality
	-- ERROR: Major failure which allows program to run, but impeeds functionality
	-- CRITICAL: Error causing program abort
'''

import sys, re, time, ftplib, json, os, shutil
from getpass import *
from optparse import *
from netrc import *
from subprocess import *

LOG_FILE = time.strftime('.%Y-%m-%d.log')
CONFIG_FILE = '.duConfig.conf'
PROG_TITLE = 'drupdate'
VERSION = '0.5.1a'

DEF_CONFIG = {
		'DirectoriesToSave' : '', 
		'FilesToSave' : '', 
		'DrupalBaseDir' : 'www',
		'DrupalVersion' : '7.8'
	}

ftpConn = None
verbose = True
testrun = False
i = j = 0


'''  Collects host, username, password, and optional account information  '''
def collectLogin(mainArg, userN='', pw='', acct=''):
	if '@' in mainArg[0]:
		upBundle, remoteSvr = mainArg[0].split('@')
		if ':' in upBundle:
			userN, pw = upBundle.split(':')
		else:
			userN = upBundle
	else:
		remoteSvr = mainArg[0]
	
	log.debug(sys.platform)
	if sys.platform == 'linux2':
		try:
			ftpInfo = netrc()
			if ftpInfo.authenticators(remoteSrv) != None:
				userN, acct, pw = ftpInfo.authenticators(remoteSvr)
		except IOError:
			log.warning('No .netrc file found')
		
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
				printAndLog('Echoed password input aborted by user, {} exiting'.format(PROG_TITLE),log.INFO,True)
				sys.exit(3)
	log.debug(userN)
	return (remoteSvr.strip(), userN.strip(), pw.strip(), acct.strip())


'''  Recursive function which deletes entire directory trees  '''
def deleteDir(rootDir):
	global ftpConn, j, testrun
	if testrun:
		global i
		i += 1
	ftpConn.cwd(rootDir)
	fList = ftpConn.nlst()
	for f in fList:
		if re.search(r'.*\..+',f) and f != '..':
			if testrun == False:
				ftpConn.delete(f)
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
				sprint('Deleting {}'.format(f))
		elif f != '..' and f != '.':
			deleteDir(f)
		
	ftpConn.cwd('..')
	if testrun == False:
		ftpConn.rmd(rootDir)
	else:
		sprint('='*i,end='')
		sprint('Removing {}'.format(rootDir))
		i -= 1	
	return


'''  Recursive function which uploads entire directory trees  '''
def uploadDir(rootDir):
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
	for f in fList:
		if re.search(r'.*\..+',f) and f != '..':
			if testrun == False:
				openF = open(f,'rb') #TODO need a try/except here
				ftpConn.storbinary('STOR {}'.format(f),openF)
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
				sprint('Uploading {}'.format(f))
		elif f != '..' and f != '.':
			uploadDir(f)
			
	ftpConn.cwd('..')
	os.chdir('..')
	if testrun:
		i -= 1
	return


def main():
	global ftpConn, verbose, testrun
	#TODO fix logging to respect debug flag
	log.basicConfig(filename=LOG_FILE,level=log.INFO)
	log.info('Logging started')
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
	
	''' Options --account, -A, currently do not work  '''
	parser = OptionParser(description=DESC, prog=PROG_TITLE, version='{} version {}'.format(PROG_TITLE, VERSION), 
						  usage='drupalUpdate.py [options] host')
	parser.add_option('-v','--ver', help="Specify the version of drupal to get, like 'X.y'", metavar='VER')
	parser.add_option('-u','--user', help='Specify a username to login to a host with')
	parser.add_option('-p','--password', help='Password to use with login', metavar='PASS')
	parser.add_option('--account', help='Specify an account to use with login', metavar='ACCT')
	parser.add_option('-k','--keep', action='store_true', default=False, help='Keeps both the local Drupal directory and the .tar')
	parser.add_option('-n','--no-get',action='store_true', default=False, help='Stops the script from downloading and unpacking Drupal')
	parser.add_option('-q','--quiet',action='store_true', default=False, help='Silences output')
	parser.add_option('-t','--testrun', action='store_true', default=False, 
					  help="Same as a normal run, except files aren't acutually changed.  A detailed log of operations is printed to stdout")
	#parser.add_option('-d','--debug', action='store_true', default=False, 
	#				  help='Turns on debugging (WARNING: This will log private information, such as usernames)')
	#parser.add_option('-A','--auto', action='store_true', 
	#				  help='Tells the updater to automatically find the latest version of Drupal'.format(PROG_TITLE))
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
		printAndLog('Starting download of Drupal {}.{}'.format(drupalVer[0],drupalVer[1]),log.INFO)
		###
		
		Popen(['wget','-q','http://drupal.org/files/projects/drupal-{}.{}.tar.gz'.format(drupalVer[0],drupalVer[1])]).wait()
		
		### STATUS
		printAndLog('Download finished, unpacking...',log.INFO)
		###
		
		Popen(['tar','-xzf','drupal-{}.{}.tar.gz'.format(drupalVer[0],drupalVer[1])])
	
	#FUT Attept at platform-independent code, visit again later
	'''
	drupalTarDownload = urllib.request.urlopen('http://drupal.org/files/projects/drupal-{}.{}.tar.gz'.format(7,8))
	drupalTarFile = open('drupal-{}.{}.tar.gz'.format(7,8),'w+b')
	print(type(drupalTarDownload.read()))
	#print(drupalTarDownload.read(),file=drupalTarFile)
	drupalTarFile.write(drupalTarDownload.read())
	drupalTarFile.close()
	'''
	
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
	except ftplib.all_errors:		#TODO break out, create fixes for each error
		printAndLog('Something went wrong...',log.CRITICAL,True,sys.stderr)
		sys.exit(1)
	
	ftpConn.cwd(configDict['DrupalBaseDir'])
	log.debug('Current dir: {}'.format(ftpConn.pwd()))
	curFileList = ftpConn.nlst()
	log.debug('Current dir listing:\n{}'.format(curFileList))
	curWD = ftpConn.pwd()
	
	### STATUS
	sprint('Removing files --   ',end='')
	sys.stdout.flush()
	###
	
	for dir in curFileList:
		#r'.*\..*'
		#r'.*\.d.*'  #TODO Need to find re that will allow finding of '.d' directories too
		if not(re.search(r'.*\..*',dir)) and dir not in configDict['DirectoriesToSave']:
			deleteDir(dir)
		elif dir not in configDict['FilesToSave'] and dir not in ['.','..'] and dir not in configDict['DirectoriesToSave']:
			if testrun == False:
				ftpConn.delete(dir)
			else:
				sprint('Deleting {}'.format(dir))
	sprint('')
	
	### STATUS
	printAndLog("Removal complete, starting upload",log.INFO)
	###

	os.chdir('drupal-{}.{}'.format(drupalVer[0],drupalVer[1]))
	
	### STATUS
	sprint("Uploading files --   ",end='')
	###
	
	for f in os.listdir(os.getcwd()):
		if not(re.search(r'.*\..*',f)) and f not in configDict['DirectoriesToSave']:
			uploadDir(f) 
		elif f not in configDict['FilesToSave'] and f not in ['.','..'] and f not in configDict['DirectoriesToSave']:
			if testrun == False:
				openF = open(f,'rb')
				log.debug('Storing {}'.format(f))
				ftpConn.storbinary('STOR {}'.format(f),openF)
			else:
				sprint('Uploading {}'.format(f))
	sprint('')
	
	### STATUS
	sprint('Drupal successfuly updated to {}.{}'.format(drupalVer[0],drupalVer[1]))
	###
	
	if options.keep == False:
		os.chdir('..')
		shutil.rmtree('drupal-{}.{}'.format(drupalVer[0],drupalVer[1]),True)
		os.unlink('drupal-{}.{}.tar.gz'.format(drupalVer[0],drupalVer[1]))
	
	try:
		ftpConn.quit()
	except ftplib.all_errors:
		ftpConn.close()
	log.info('Connection to {} closed'.format(remoteSvr))
	log.shutdown()


'''  A simple method which prints and logs the same message  '''
def printAndLog(message, level=log.DEBUG, verbOverride=False, printStream=sys.stdout):
	log.log(level, message)
	if verbose or verbOverride:
		print(message, file=printStream)

''' Simple wrapper to print method that respects verbose option  '''
def sprint(message,sep=' ',end='\n',file=sys.stdout):
	if verbose:
		print(message,sep=sep,end=end,file=file)

DESC = '''
    A simple python script which automatically removes and replaces a 'typical' Drupal install on a
remote FTP server.  Only tested on Drupal 7.x installs, use with care
'''

if __name__ == '__main__':
	main()
