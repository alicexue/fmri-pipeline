#!/usr/bin/env python
"""
Exports raw BIDS from flywheel for each subject into a directory called 'raw'
Only exports raw BIDS for subjects whose fmriprep directories exist
Note: raw BIDS can only be exported if docker is running
"""

# Created by Alice Xue, 06/2018

import os
import subprocess as sp
import sys

from directory_struct_utils import *

def main():
	if len(sys.argv)!=4:
		print "usage: export_raw_bids <studyid> <basedir> <Flywheel project_label>"
		sys.exit(-1)
	studyid=sys.argv[1]
	basedir=sys.argv[2]
	project_label=sys.argv[3]
	export_raw_bids(studyid,basedir,project_label)

def export_raw_bids(studyid,basedir,project_label):
	studydir=os.path.join(basedir,studyid)
	rawdir=os.path.join(studydir,'raw')
	if not os.path.exists(rawdir):
		os.makedirs(rawdir)

	# checks whether docker is installed (but not if docker is running)
	dockerExists=False
	try:
		FNULL = open(os.devnull, 'w')
		sp.call(['docker'],stdout=FNULL, stderr=sp.STDOUT)
		dockerExists=True
	except:
		dockerExists=False

	fwExists=False	
	try:	
		FNULL = open(os.devnull, 'w')	
		sp.call(['fw'],stdout=FNULL, stderr=sp.STDOUT)	
		fwExists=True	
	except:	
		fwExists=False

	print '\n## Exporting raw BIDS now ##\n'

	if fwExists and dockerExists:
		# gets all subjects with fmriprep directories
		all_subs=get_all_subs(studydir)
		for sub in all_subs: # sub is missing the prefix 'sub-'
			rawsubdir=os.path.join(rawdir,'sub-%s'%sub)
			if os.path.exists(rawsubdir):
				print "Skipping download of raw bids for sub-%s"%sub
			else:
				# creates tmp dir specific to the subject
				tmpsubdir=os.path.join(studydir,'tmp_sub-%s_BIDS'%sub)
				os.mkdir(tmpsubdir)
				# call subprocess to export BIDS
				commands=['fw','export','bids',tmpsubdir,'-p',project_label,'--subject',sub]
				print 'Calling:',' '.join(commands)
				sp.call(commands)
				# moves the exported directory into the raw directory
				rawsubout=os.path.join(tmpsubdir,'sub-%s'%sub)
				print 'Moving %s to %s'%(rawsubout,rawdir)
				sp.call(['mv',rawsubout,rawdir])
				# removes tmp directory that was created
				print 'Removing %s'%(tmpsubdir)
				sp.call(['rm','-rf',tmpsubdir])
	else:
		if not fwExists:
			print 'Flywheel CLI is not installed, which is required for exporting raw BIDS.'
		if not dockerExists:
			print 'Docker is not installed. Docker is required to export raw BIDS from flywheel'

if __name__ == '__main__':
    main()
