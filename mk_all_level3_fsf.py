"""
Get information to run mk_level3_fsf on multiple subjects, tasks, runs, etc
Called by run_level3_feat.py
"""
# Created by Alice Xue, 06/2018

from directory_struct_utils import *
#from mk_level1_fsf_bbr import mk_level1_fsf_bbr
import mk_level3_fsf
import os
import sys
import subprocess
import argparse
import json

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
    parser.add_argument('--sessions', dest='sessions', nargs='+',
        default=[],help='Name of session (not including prefix "sub-"')
    parser.add_argument('-i', '--slurm_array_task_id', dest='slurm_array_task_id', type=int,
        default=-1,help='index of job array in slurm')

    args = parser.parse_args(argv)
    return args

def main(argv=None):
	args=parse_command_line(argv)
	print args

	studyid=args.studyid
	basedir=args.basedir
	modelnum=args.modelnum
	slurm_array_task_id=args.slurm_array_task_id

	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)

	print study_info

	jobs = []
	subs=study_info.keys()
	list.sort(subs)
	# iterate through runs based on the runs the first subject did
	subid=subs[0]
	sub=subid[len('sub-'):]
	if hasSessions:
		sessions=study_info[subid].keys()
		list.sort(sessions)
		for ses in sessions:
			sesname=ses[len('ses-'):]
			tasks=study_info[subid][ses].keys()
			list.sort(tasks)
			for task in tasks:
				args=[studyid,basedir,task,sesname,modelnum]
				jobs.append(args)
	else:
		sesname=''
		tasks=study_info[subid].keys()
		list.sort(tasks)
		for task in tasks:
			args=[studyid,basedir,task,sesname,modelnum]
			jobs.append(args)

	all_copes=[]
	for job_args in jobs:
		args=job_args
		copes=mk_level3_fsf.mk_level3_fsf(studyid=args[0],basedir=args[1],taskname=args[2],sesname=args[3],modelnum=args[4])
		all_copes+=copes

	if slurm_array_task_id != -1:
		print "Calling", ' '.join(['feat',all_copes[slurm_array_task_id]])
		subprocess.call(['feat',all_copes[slurm_array_task_id]])
	else:
		print len(all_copes), "jobs"
		return all_copes

if __name__ == '__main__':
    main()