"""
Exports raw BIDS from flywheel for each subject 
Only exports raw BIDS for subjects whose fmriprep directories exist
Note: raw BIDS can only be exported if docker is running
"""

# Created by Alice Xue, 06/2018

import subprocess as sp
import os
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

	dockerExists=False
	try:
		FNULL = open(os.devnull, 'w')
		sp.call(['docker'],stdout=FNULL, stderr=sp.STDOUT)
		dockerExists=True
	except:
		dockerExists=False

	print '\n## Exporting raw BIDS now ##\n'

	if dockerExists:
		all_subs=get_all_subs(studydir)
		for sub in all_subs:
			rawsubdir=os.path.join(rawdir,'sub-%s'%sub)
			if os.path.exists(rawsubdir):
				print "Skipping download of raw bids for sub-%s"%sub
			else:
				tmpsubdir=os.path.join(studydir,'tmp_sub-%s_BIDS'%sub)
				os.mkdir(tmpsubdir)
				commands=['fw','export','bids',tmpsubdir,'-p',project_label,'--subject',sub]
				print 'Calling:',' '.join(commands)
				sp.call(commands)
				rawsubout=os.path.join(tmpsubdir,'sub-%s'%sub)
				print 'Moving %s to %s'%(rawsubout,rawdir)
				sp.call(['mv',rawsubout,rawdir])
				print 'Removing %s'%(tmpsubdir)
				sp.call(['rm','-rf',tmpsubdir])

if __name__ == '__main__':
    main()
