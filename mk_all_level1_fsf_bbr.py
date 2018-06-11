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
    parser.add_argument('--smoothing', dest='smoothing',type=int,
        default=0,help='Smoothing (mm FWHM)')
    parser.add_argument('--use_inplane', dest='use_inplane', type=int,
        default=0,help='Use inplane image')
    parser.add_argument('--nonlinear', dest='nonlinear', action='store_true',
        default=False,help='Use nonlinear registration')
    parser.add_argument('--nohpf', dest='hpf', action='store_false',
        default=True,help='Turn off high pass filtering')
    parser.add_argument('--nowhiten', dest='whiten', action='store_false',
        default=True,help='Turn off prewhitening')
    parser.add_argument('--noconfound', dest='confound', action='store_false',
        default=True,help='Omit motion/confound modeling')
    parser.add_argument('--modelnum', dest='modelnum',type=int,
        default=1,help='Model number')
    parser.add_argument('--anatimg', dest='anatimg',
        default='',help='Anatomy image (should be _brain)')
    parser.add_argument('--doreg', dest='doreg', action='store_true',
        default=False,help='Do registration')
    parser.add_argument('--spacetag', dest='spacetag',
        default='',help='Space tag for preprocessed data')
    parser.add_argument('--altBETmask', dest='altBETmask', action='store_true',
        default=False,help='Use brainmask from fmriprep')
    parser.add_argument('-i', '--slurm_array_task_id', dest='slurm_array_task_id', type=int,
        default=-1,help='index of job array in slurm')

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
	args=parse_command_line(argv)
	print args

	studyid=args.studyid
	basedir=args.basedir
	specificruns=args.specificruns
	modelnum=args.modelnum
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
	slurm_array_task_id=args.slurm_array_task_id

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
	#params_to_remove=['--subs','--tasks','--sessions','-i','--slurm_array_task_id']
	params_to_remove=['-s','--specificruns','-i','--slurm_array_task_id']
	for param in params_to_remove:
		if param in sys_argv:
			i=sys_argv.index(param)
			del sys_argv[i]
			del sys_argv[i]
	del sys_argv[0]

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
						args=sys_argv[:]
						args=add_args(args,sub,task,run)
						args.append('--ses')
						args.append(sesname)
						jobs.append(args)
		else:
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				for run in runs:
					args=sys_argv[:]
					args=add_args(args,sub,task,run)
					jobs.append(args)

	if slurm_array_task_id != -1:
		print jobs[slurm_array_task_id]
		mk_level1_fsf_bbr.main(argv=jobs[slurm_array_task_id])
	else:
		print len(jobs), "jobs"
		return jobs

if __name__ == '__main__':
    main()
