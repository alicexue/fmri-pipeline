"""
Gets a list of level 1 feats to create (excludes feats that already exist)
The list of jobs is used by run_level1.py and passed to run_feat_job.py as a dictionary
run_feat_job.py calls mk_level1_fsf_bbr.py
"""

# Created by Alice Xue, 06/2018

import argparse
import copy
import json
import os
import setup_utils
import subprocess
import sys

from directory_struct_utils import *

def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='get_jobs')

    parser.add_argument('--studyid', dest='studyid',
        required=True,help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
        required=True,help='Base directory (above studyid directory)')
    parser.add_argument('--modelnum', dest='modelnum',type=int,
		default=1,help='Model number')
    parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
		default={},help="""
			JSON object in a string that details which runs to create fsf's for. If specified, ignores specificruns specified in model_params.json.
			Ex: If there are sessions: \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the runs.
			If there aren't sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}\'. Make sure this describes the fmriprep folder, which should be in BIDS format.
			Make sure to have single quotes around the JSON object and double quotes within."""
			)
    args = parser.parse_args(argv)
    return args

def add_args(args,sub,task,run):
	args.append('--sub')
	args.append(sub)
	args.append('--taskname')
	args.append(task)
	args.append('--runname')
	args.append(run)
	args.append('--callfeat')
	return args

def main(argv=None):
	sys_args=parse_command_line(argv)
	print sys_args

	studyid=sys_args.studyid
	basedir=sys_args.basedir
	modelnum=sys_args.modelnum
	specificruns=sys_args.specificruns
	
	args=setup_utils.model_params_json_to_namespace(studyid,basedir,modelnum)
	print args

	if specificruns == {}: # if specificruns from sys.argv is empty (default), use specificruns from model_param
		specificruns=args.specificruns
	get_level1_jobs(studyid,basedir,modelnum,specificruns,sys_args.specificruns)

def get_level1_jobs(studyid,basedir,modelnum,specificruns,sys_args_specificruns):
	"""
	Args:
		specificruns (dict): from model_params.json
		sys_args_specificruns (dict): passed into the program through the command line (sys.args)
	"""
	# gets parameters set in model_param.json
	args=setup_utils.model_params_json_to_namespace(studyid,basedir,modelnum) 

	smoothing=args.smoothing
	use_inplane=args.use_inplane
	nonlinear=args.nonlinear
	anatimg=args.anatimg
	confound=args.confound
	hpf = args.hpf
	whiten=args.whiten
	doreg=args.doreg
	spacetag=args.spacetag
	altBETmask=args.altBETmask
	
	# gets dictionary of study information
	study_info=specificruns
	hasSessions=False
	if specificruns=={}: # if specificruns in model_params was empty
		# tries getting study info first with hasSessions set to false
		# determines that hasSessions is true if the values of the subjects are empty
		studydir=os.path.join(basedir,studyid)
		study_info=get_study_info(studydir,hasSessions)
		if len(study_info.keys()) > 0:
			if not study_info[study_info.keys()[0]]: # if empty
				hasSessions=True
				study_info=get_study_info(studydir,hasSessions)
	else:
		l1=study_info.keys()
		l2=study_info[l1[0]].keys()[0]
		if l2.startswith('ses-'):
			hasSessions=True
	print study_info

	# convert model params into a list of arguments that can be used to call mk_level1_fsf_bbr
	# contains all the model params but not specific info like subject, task, run
	sys_argv=setup_utils.model_params_json_to_list(studyid,basedir,modelnum)

	# created a deep copy of study_info (want to remove runs from the copy and not the original)
	study_info_copy=copy.deepcopy(study_info)

	existing_feat_files=[]
	jobs = [] # list of list of arguments to run mk_level1_fsf_bbr on
	subs=study_info.keys()
	list.sort(subs) 
	# iterate through each subject, session, task, and runs
	for subid in subs:
		sub=subid[len('sub-'):] # sub is the subject ID without the prefix 'sub-'
		if hasSessions:
			sessions=study_info[subid].keys()
			list.sort(sessions)
			for ses in sessions:
				sesname=ses[len('ses-'):]
				tasks=study_info[subid][ses].keys()
				list.sort(tasks)
				for task in tasks:
					runs=study_info[subid][ses][task]
					list.sort(runs)
					for run in runs:
						# check if feat exists for this run
						model_subdir='%s/model/level1/model%03d/%s/%s/task-%s_run-%s'%(os.path.join(basedir,studyid),modelnum,subid,ses,task,run)
						feat_file="%s/%s_%s_task-%s_run-%s.feat"%(model_subdir,subid,ses,task,run)
						if sys_args_specificruns=={} and os.path.exists(feat_file): # if subject didn't pass in specificruns and a feat file for this run exists
							existing_feat_files.append(feat_file)
							runs_copy=study_info_copy[subid][ses][task]
							runs_copy.remove(run) # removes the run since a feat file for it already exists
						else: # if subject passed in specificruns 
							if os.path.exists(feat_file):
								print "WARNING: Existing feat file found: %s"%feat_file
							args=sys_argv[:] # copies over the list of model params
							args=add_args(args,sub,task,run) # adds subject, task, and run 
							args.append('--ses') # adds session
							args.append(sesname) 
							jobs.append(args) # each list 'args' specifies the arguments to run mk_level1_fsf_bbr on
					if len(study_info_copy[subid][ses][task])==0: # if there are no runs for this task
						del study_info_copy[subid] # remove the task from the dictionary
		else: # no sessions
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				for run in runs:
					# check if feat exists for this run
					model_subdir='%s/model/level1/model%03d/%s/task-%s_run-%s'%(os.path.join(basedir,studyid),modelnum,subid,task,run)
					feat_file="%s/%s_task-%s_run-%s.feat"%(model_subdir,subid,task,run)
					if sys_args_specificruns=={} and os.path.exists(feat_file): # if subject didn't pass in specificruns and a feat file for this run exists
						existing_feat_files.append(feat_file)
						runs_copy=study_info_copy[subid][task]
						runs_copy.remove(run) # removes the run since a feat file for it already exists
					else: # if subject passed in specificruns
						if os.path.exists(feat_file):
							print "WARNING: Existing feat file found: %s"%feat_file
						args=sys_argv[:]
						args=add_args(args,sub,task,run)
						jobs.append(args)
				if len(study_info_copy[subid][task])==0: # if there are no runs for this task
					del study_info_copy[subid]  # remove the task from the dictionary

	if len(study_info_copy.keys()) == 0: 
		print "ERROR: All runs for all subjects have been run on this model. Remove the feat files if you want to rerun them."
		sys.exit(-1)
	elif sys_args_specificruns=={} and len(existing_feat_files)!=0: # if the user didn't pass in specificruns and existing feat files were found
		print "ERROR: Some subjects' runs have already been run on this model. If you want to rerun these subjects, remove their feat directories first. To run the remaining subjects, rerun run_level1.py and add:"
		print "-s \'%s\'"%(json.dumps(study_info_copy))
		sys.exit(-1)
	else: # no existing feat files were found
		print len(jobs), "jobs"
		return jobs

if __name__ == '__main__':
    main()
