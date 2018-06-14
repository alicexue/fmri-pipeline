"""
Get information to run mk_level2_fsf on multiple subjects, tasks, runs, etc
Called by run_level2_feat.py
"""

# Created by Alice Xue, 06/2018

from directory_struct_utils import *
import mk_level2_fsf
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
    parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
        default={},help="""
            JSON object in a string that details which runs to create fsf's for. 
            Ex: If there are sessions: \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the runs.
            If there aren't sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}\'. Make sure this describes the fmriprep folder, which should be in BIDS format.
            Make sure to have single quotes around the JSON object and double quotes within."""
            )
    parser.add_argument('--modelnum', dest='modelnum',type=int,
        default=1,help='Model number')
    parser.add_argument('--sessions', dest='sessions', nargs='+',
        default=[],help='Name of session (not including prefix "sub-"')

    args = parser.parse_args(argv)
    return args

def add_args(args,sub,task,runs):
	args.append('--sub')
	args.append(sub)
	args.append('--taskname')
	args.append(task)
	args.append('--runs')
	args+=runs
	args.append('--callfeat')
	return args

def main(argv=None):
	args=parse_command_line(argv)
	print args

	studyid=args.studyid
	specificruns=args.specificruns
	basedir=args.basedir
	modelnum=args.modelnum

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

	sys_argv=sys.argv[:]
	params_to_remove=['--email','-e','-A','--account','-t','--time','-N','--nodes','-s','--specificruns']
	for param in params_to_remove:
		if param in sys_argv:
			i=sys_argv.index(param)
			del sys_argv[i]
			del sys_argv[i]
	del sys_argv[0]

	jobs = []
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
					args=sys_argv[:]
					args=add_args(args,sub,task,runs)
					args.append('--ses')
					args.append(sesname)
					jobs.append(args)
		else:
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				args=sys_argv[:]
				args=add_args(args,sub,task,runs)
				jobs.append(args)

	print len(jobs), "jobs"
	return jobs

if __name__ == '__main__':
    main()
