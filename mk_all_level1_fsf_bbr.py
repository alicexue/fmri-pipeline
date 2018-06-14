"""
Get information to run mk_level1_fsf_bbr on multiple subjects, tasks, runs, etc
Will run one instance of mk_level1_fsf_bbr if slurm_array_task_id is specified
Otherwise, will run all jobs sequentially in same process
Called by run_level1_feat.py
"""

# Created by Alice Xue, 06/2018

from directory_struct_utils import *
#from mk_level1_fsf_bbr import mk_level1_fsf_bbr
import mk_level1_fsf_bbr
import setup_utils
import os
import sys
import subprocess
import argparse
import json
import copy

def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='setup_jobs')
    #parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags

    parser.add_argument('--studyid', dest='studyid',
        required=True,help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
        required=True,help='Base directory (above studyid directory)')
    parser.add_argument('--modelnum', dest='modelnum',type=int,
		default=1,help='Model number')
    parser.add_argument('-i', '--slurm_array_task_id', dest='slurm_array_task_id', type=int,
        default=-1,help='index of job array in slurm')
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
	slurm_array_task_id=sys_args.slurm_array_task_id
	specificruns=sys_args.specificruns
	
	args=setup_utils.model_params_json_to_namespace(studyid,basedir,modelnum)
	print args

	if specificruns == {}: # if specificruns from sys.argv is empty (default), use specificruns from model_param
		specificruns=args.specificruns
	mk_all_level1_fsf_bbr(studyid,basedir,modelnum,slurm_array_task_id,specificruns,sys_args.specificruns)

def mk_all_level1_fsf_bbr(studyid,basedir,modelnum,slurm_array_task_id,specificruns,sys_args_specificruns):
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
	

	study_info=specificruns
	hasSessions=False
	if specificruns=={}:
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

	sys_argv=setup_utils.model_params_json_to_list(studyid,basedir,modelnum)

	study_info_copy=copy.deepcopy(study_info)

	existing_feat_files=[]
	jobs = []
	subs=study_info.keys()
	list.sort(subs)
	for subid in subs:
		sub=subid[len('sub-'):]
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
						model_subdir='%s/model/level1/model%03d/%s/%s/task-%s_run-%s'%(os.path.join(basedir,studyid),modelnum,subid,ses,task,run)
						feat_file="%s/%s_%s_task-%s_run-%s.feat"%(model_subdir,subid,ses,task,run)
						if sys_args_specificruns=={} and os.path.exists(feat_file):
							existing_feat_files.append(feat_file)
							runs_copy=study_info_copy[subid][ses][task]
							runs_copy.remove(run)
						else:
							if os.path.exists(feat_file):
								print "WARNING: Existing feat file found: %s"%feat_file
							args=sys_argv[:]
							args=add_args(args,sub,task,run)
							args.append('--ses')
							args.append(sesname)
							jobs.append(args)
					if len(study_info_copy[subid][ses][task])==0:
						del study_info_copy[subid]
		else:
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				for run in runs:
					model_subdir='%s/model/level1/model%03d/%s/task-%s_run-%s'%(os.path.join(basedir,studyid),modelnum,subid,task,run)
					feat_file="%s/%s_task-%s_run-%s.feat"%(model_subdir,subid,task,run)
					if sys_args_specificruns=={} and os.path.exists(feat_file):
						existing_feat_files.append(feat_file)
						runs_copy=study_info_copy[subid][task]
						runs_copy.remove(run)
					else:
						if os.path.exists(feat_file):
							print "WARNING: Existing feat file found: %s"%feat_file
						args=sys_argv[:]
						args=add_args(args,sub,task,run)
						jobs.append(args)
				if len(study_info_copy[subid][task])==0:
					del study_info_copy[subid]

	if len(study_info_copy.keys()) == 0:
		print "ERROR: All runs for all subjects have been run on this model. Remove the feat files if you want to rerun them."
		sys.exit(-1)
	elif sys_args_specificruns=={} and len(existing_feat_files)!=0:
		print "ERROR: Some subjects' runs have already been run on this model. If you want to rerun these subjects, remove their feat directories first. To run the remaining subjects, rerun run_level1.py and add:"
		print "-s \'%s\'"%(json.dumps(study_info_copy))
		sys.exit(-1)
	elif slurm_array_task_id > -1:
		print jobs[slurm_array_task_id]
		mk_level1_fsf_bbr.main(argv=jobs[slurm_array_task_id])
	else:
		print len(jobs), "jobs"
		return jobs

if __name__ == '__main__':
    main()
