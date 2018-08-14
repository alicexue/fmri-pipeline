#!/usr/bin/env python
"""
Exports raw BIDS from flywheel for all subjects into a directory called 'raw'
(unable to get list of subjects to export bids directories individually)
Note: raw BIDS can only be exported if docker is running
"""

# Created by Alice Xue, 06/2018

import flywheel
import os
import subprocess as sp
import sys

from directory_struct_utils import *

def main():
	if len(sys.argv)!=6:
		print "usage: export_raw_bids <studyid> <basedir> <Flywheel API key> <Flywheel group_id> <Flywheel project_label>"
		sys.exit(-1)
	studyid=sys.argv[1]
	basedir=sys.argv[2]
	key=sys.argv[3]
	group_id=sys.argv[4]
	project_label=sys.argv[5]
	export_raw_bids(studyid,basedir,key,group_id,project_label)

def export_raw_bids(studyid,basedir,key,group_id,project_label):
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

	# check if fw CLI is installed - needed for exporting BIDS
	fwExists=False	
	try:	
		FNULL = open(os.devnull, 'w')	
		sp.call(['fw'],stdout=FNULL, stderr=sp.STDOUT)	
		fwExists=True	
	except:	
		fwExists=False

	print '\n## Exporting raw BIDS now ##\n'

	if fwExists and dockerExists:	
		# Create client
		fw = flywheel.Flywheel(key) # API key

		sub_codes=[]

		for project in fw.get_group_projects(group_id):
			if project.label==project_label:
				print('Project: %s: %s' % (project.id, project.label))
				for session in fw.get_project_sessions(project.id):
					sub=session.subject.code
					if sub not in sub_codes:
						sub_codes.append(session.subject.code)

		all_subs=get_all_subs(studydir) # subjects with fmriprep outputs downloaded
		sub_code_dict = {}
		for code in sub_codes:
			code_w_underscore_removed = code.replace("_", "") 
			# want to removed underscore from subject code because underscore in subject id is not compatible with BIDS
			if code_w_underscore_removed in all_subs:
				sub_code_dict[code] = code_w_underscore_removed # key is subject code, value is subject id
				# subject code is used to export BIDS, subject id used by the fmriprep output 

		for sub_code in sub_code_dict.keys():
			sub=sub_code_dict[sub_code]
			rawsubdir=os.path.join(rawdir,'sub-%s'%sub)
			if os.path.exists(rawsubdir):
				print "Skipping download of raw bids for sub-%s"%sub
			else:
				# creates tmp dir specific to the subject
				tmpsubdir=os.path.join(studydir,'tmp_sub-%s_BIDS'%sub)
				os.mkdir(tmpsubdir)
				# call subprocess to export BIDS
				commands=['fw','export','bids',tmpsubdir,'-p',project_label,'--subject',sub_code]
				print 'Calling:',' '.join(commands)
				sp.call(commands)
				# moves the exported directory into the raw directory
				rawsubout=os.path.join(tmpsubdir,'sub-%s'%sub)
				print 'Moving %s to %s'%(rawsubout,rawdir)
				sp.call(['mv',rawsubout,rawdir])
				# removes tmp directory that was created
				print 'Removing %s'%(tmpsubdir)
				sp.call(['rm','-rf',tmpsubdir])

		"""
		# gets all subjects with fmriprep directories
		#all_subs=get_all_subs(studydir)
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
		"""

		# to download all raw bids rather than subject by subject
		"""
		tmpdir=os.path.join(studydir,'tmp_BIDS')
		commands=['fw','export','bids',tmpdir,'-p',project_label]
		sp.call(commands)
		sp.call(['mv',tmpdir, rawdir])
		subs = os.listdir(tmpdir)
		for sub in subs:
			rawsubout = os.path.join(tmpdir,sub)
			if not os.path.exists(rawsubout):
				sp.call(['mv',rawsubout,rawdir])
		sp.call(['rm','-rf',tmpdir])
		"""
	else:
		if not fwExists:
			print 'Flywheel CLI is not installed, which is required for exporting raw BIDS.'
		if not dockerExists:
			print 'Docker is not installed. Docker is required to export raw BIDS from flywheel'

if __name__ == '__main__':
    main()
