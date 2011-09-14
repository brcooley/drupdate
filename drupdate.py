#! /usr/bin/python3
# -*- coding: utf-8 -*-

'''
DrupalUpdate
brcooley

Account strings currently are not implemented
Automatic version finding not implemented
'''

import logging as log
'''
	Logging level definitions:
	-- DEBUG: Debugging and system information/user input
	-- INFO: Status, ftp command info
	-- WARNING: Error which does not impeed functionality
	-- ERROR: Major failure which allows program to run, but impeeds functionality
	-- CRITICAL: Error causing program abort
'''

import sys, re, time, ftplib, json, urllib.request, os
from getpass import *
from optparse import *
from netrc import *
from subprocess import *

LOG_FILE = time.strftime('%Y-%m-%d.log')
CONFIG_FILE = '.duConfig.conf'
PROG_TITLE = 'DrupalUpdate'
VERSION = '0.3a'
PROD = False

DEF_CONFIG = {
		'DirectoriesToSave' : '', 
		'FilesToSave' : '', 
		'Verbose' : '',
		'DrupalBaseDir' : 'www',
		'DrupalVersion' : '7.8'
	}

ftpConn = None
verbose = True
i = 0
x = 0


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
	log.debug(pw)
	return (remoteSvr.strip(), userN.strip(), pw.strip(), acct.strip())


'''  Recursive function which deletes entire directory trees  '''
def deleteDir(rootDir):
	global ftpConn, x
	if PROD == False:
		global i
		i += 1
	ftpConn.cwd(rootDir)
	fList = ftpConn.nlst()
	for f in fList:
		if re.search(r'.*\..+',f) and f != '..':
			if PROD == True:
				ftpConn.delete(f)
			else:
				#print('-'*i,end='')
				#print('Deleting {}'.format(f))
				pass
		elif f != '..' and f != '.':
			deleteDir(f)
	ftpConn.cwd('..')
	if PROD == True:
		ftpConn.rmd(rootDir)
	else:
		#print('='*i,end='')
		#print('Removing {}'.format(rootDir))
		i -= 1
	if x % 4 == 3:
		print('   \b\b\b',end='')
	elif x % 4 == 2:
		print('.\b\b\b',end='')
	else:
		print('.',end='')
	x += 1
	sys.stdout.flush()
	return


'''  Recursive function which uploads entire directory trees  '''
def uploadDir(rootDir):
	global ftpConn
	j = 0
	if PROD == False:
		global i
		i += 1
		#print('='*i,end='')
		#print('Creating {}'.format(rootDir))
	else:
		ftpConn.mkd(rootDir)
		ftpConn.cwd(rootDir)
	os.chdir(rootDir)
	fList = os.listdir(os.getcwd())
	for f in fList:
		if re.search(r'.*\..+',f) and f != '..':
			if PROD == True:
				openF = open(f,'r')
				ftpConn.storbinary('STOR {}'.format(f),openF)
			else:
				#print('-'*i,end='')
				#print('Uploading {}'.format(f))
				pass
		elif f != '..' and f != '.':
			uploadDir(f)
	ftpConn.cwd('..')
	os.chdir('..')
	if PROD == False:
		i -= 1
	if j % 4 == 3:
		print('\b|',end='')
	elif j % 4 == 2:
		print('\b\\',end='')
	elif j % 4 == 1:
		print('\b-',end='')
	else:
		print('\b/',end='')
	j += 1
	sys.stdout.flush()
	return


'''  Currently unimplemented, will serve as the ftp prompt for a general ftp session  '''
def ftpPrompt():
	return


def main():
	global ftpConn, verbose
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
	
	''' Options --account, -A currently do not work  '''
	parser = OptionParser(description=DESC, prog=PROG_TITLE, version='{} version {}'.format(PROG_TITLE, VERSION), 
						  usage='drupalUpdate.py [options] host')
	parser.add_option('-V','--ver', help="Specify the version of drupal to get, like 'X.y'", metavar='VER')
	parser.add_option('-u','--user', help='Specify a username to login to a host with')
	parser.add_option('-p','--password', help='Password to use with login', metavar='PASS')
	parser.add_option('--account', help='Specify an account to use with login', metavar='ACCT')
	parser.add_option('-A','--auto', action='store_true', 
					  help='Tells the updater to automatically find the latest version of Drupal'.format(PROG_TITLE))
	parser.add_option('-n','--no-get',action='store_true', default=False, help='Stops the script from downloading and unpacking Drupal')
	parser.add_option('-q','--quiet',action='store_true', default=False, help='Silences output')
	parser.add_option('-d','--debug', action='store_true', default=False, 
					  help='Turns on debugging (WARNING: This will log sensitive information, such as passwords)')
	options, reqArgs = parser.parse_args()

	if len(reqArgs) < 1:
		parser.print_help()
		sys.exit(2)

	if options.quiet == True:
		verbose = False
	if options.debug:
		log.basicConfig(level=log.DEBUG)
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
	#ftpConn.set_debuglevel(1)
	try:
		ftpConn.connect(remoteSvr)
		log.info('Connection made to {}'.format(remoteSvr))
		ftpConn.getwelcome()
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
	print('Removing files',end='')
	sys.stdout.flush()
	###
	
	for dir in curFileList:
		#r'.*\..*'
		#r'.*\.d.*'  #TODO Need to find re that will allow finding of '.d' directories too
		if not(re.search(r'.*\..*',dir)) and dir not in configDict['DirectoriesToSave']:
			#print('{} to be deleted from {}'.format(dir,curWD))
			deleteDir(dir)
		elif dir not in configDict['FilesToSave'] and dir not in ['.','..']:
			if PROD == True:
				ftpConn.delete(dir)
			else:
				#print('Deleting {}'.format(dir))
				pass
	print('')
	
	### STATUS
	printAndLog("Removal complete, starting upload",log.INFO)
	###

	os.chdir('drupal-{}.{}'.format(drupalVer[0],drupalVer[1]))
	
	### STATUS
	print("Uploading files",end='')
	###
	
	for f in os.listdir(os.getcwd()):
		if not(re.search(r'.*\..*',f)) and f not in configDict['DirectoriesToSave']:
			uploadDir(f) 
		elif f not in configDict['FilesToSave'] and f not in ['.','..']:
			if PROD == True:
				openF = open(f,'r')
				ftpConn.storbinary('STOR {}'.format(f),openF)
			else:
				#print('Uploading {}'.format(f))
				pass
	print('')
	
	### STATUS
	print('Drupal successfuly updated to {}.{}'.format(drupalVer[0],drupalVer[1]))
	###
	
	try:
		ftpConn.quit()
	except ftplib.all_errors:
		ftpConn.close()
	log.info('Connection to {} closed'.format(remoteSvr))


'''  A simple method which prints and logs the same message  '''
def printAndLog(message, level=log.DEBUG, verbOverride=False, printStream=sys.stdout):
	log.log(level, message)
	if verbose or verbOverride:
		print(message, file=printStream)


DESC = '''
    A simple python script which automatically removes and replaces a 'typical' Drupal install on a
remote FTP server.  Only tested on Drupal 7.x installs, use with care
'''

if __name__ == '__main__':
	main()