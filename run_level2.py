#!/usr/bin/env python
"""
Generates run_level2_feat.sbatch to run mk_all_level2_fsf in a job array
Runs the generated sbatch file
"""

# Created by Alice Xue, 06/2018

import argparse
import datetime
from joblib import Parallel, delayed
import json
import multiprocessing
import os
import subprocess
import sys

import get_level2_jobs

def parse_command_line(argv):
	parser = argparse.ArgumentParser(description='setup_jobs')

	parser.add_argument('-e','--email',dest='email',
		required=True,help='Email to send job updates to')
	parser.add_argument('-A','--account',dest='account',
		required=True,help='Slurm account')
	parser.add_argument('-t', '--time',dest='time',
		default="00:30:00",help='Estimated time to run each job - hh:mm:ss')
	parser.add_argument('-N', '--nodes',dest='nodes',type=int,
		default=1,help='Number of nodes')
	parser.add_argument('--studyid', dest='studyid',
		required=True,help='Study ID')
	parser.add_argument('--basedir', dest='basedir',
		required=True,help='Base directory (above studyid directory)')
	parser.add_argument('--nofeat',dest='nofeat',action='store_true',
		default=False,help='Only create the fsf\'s, don\'t call feat')
	parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
		default={},help="""
			JSON object in a string that details which runs to create fsf's for. 
			Ex: If there are sessions: \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the runs.
			If there aren't sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}\'. Make sure this describes the fmriprep folder, which should be in BIDS format.
			Make sure to have single quotes around the JSON object and double quotes within."""
			)
	parser.add_argument('-m', '--modelname', dest='modelname',
		required=True,help='Model name')
	
	args = parser.parse_args(argv)
	return args

def call_feat_job(i,jobsdict,level):
	fmripipelinedir=os.path.dirname(__file__)
	subprocess.call(['python',os.path.join(fmripipelinedir,'run_feat_job.py'), '--jobs', '%s'%json.dumps(jobsdict),'-i',str(i), '--level', str(level)])

def main(argv=None):
	level=2
	d=datetime.datetime.now()
	args=parse_command_line(argv)
	email=args.email
	account=args.account
	time=args.time
	nodes=args.nodes
	specificruns=args.specificruns
	nofeat=args.nofeat

	sys_argv=sys.argv[:] # copies over the arguments passed in through the command line
	# removes the arguments that shouldn't be passed into get_level2_jobs.main() (removes the arguments only relevant to run_level2)
	params_to_remove=['--email','-e','-A','--account','-t','--time','-N','--nodes']
	for param in params_to_remove:
		if param in sys_argv:
			i=sys_argv.index(param)
			del sys_argv[i]
			del sys_argv[i]
	del sys_argv[0]

	print sys_argv

	# get the list of jobs to run
	jobs=get_level2_jobs.main(argv=sys_argv[:])
	njobs=len(jobs)
	# turn the list of jobs into a dictionary with the index as the key
	jobsdict={}
	for i in range(0,njobs):
		jobsdict[i]=jobs[i]

	if nofeat:
		for i in range(njobs):
			call_feat_job(i,jobsdict,level)
		print '\n%s *.fsf files created.'%(njobs)
	if not nofeat:
		print "WARNING: If any feat files exist (warnings would be printed above), they will not be overwritten if you continue."
		rsp=None
		while rsp != '':
			rsp=raw_input('Press ENTER to continue:')
		
		# create an sbatch file to run the job array
		j='level2-feat'
		with open('run_level2.sbatch', 'w') as qsubfile:
			qsubfile.write('#!/bin/sh\n')
			qsubfile.write('#\n')
			qsubfile.write('#SBATCH -J run_level2_feat\n')
			qsubfile.write('#SBATCH -A %s\n'%(account))
			qsubfile.write('#SBATCH -N %d\n'%(nodes))
			qsubfile.write('#SBATCH -c 1\n')
			qsubfile.write('#SBATCH --time=%s\n'%(time))
			qsubfile.write('#SBATCH --mail-user=%s\n'%(email))
			qsubfile.write('#SBATCH --mail-type=ALL\n')
			qsubfile.write('#SBATCH --array=%s-%s\n'%(0,njobs-1))
			qsubfile.write('#SBATCH -o %s_%s_%s.o\n'%(j,d.strftime("%d_%B_%Y_%Hh_%Mm_%Ss"),'%a'))
			qsubfile.write('#----------------\n')
			qsubfile.write('# Job Submission\n')
			qsubfile.write('#----------------\n')
			qsubfile.write("python run_feat_job.py --jobs '%s' -i $SLURM_ARRAY_TASK_ID --level 2"%json.dumps(jobsdict))
			
		try:
			subprocess.call(['sbatch','run_level2.sbatch'])
		except:
			print "\nNOTE: sbatch command was not found."
			rsp=None
			while rsp != 'n' and rsp != '':
				rsp=raw_input('Do you want to run the jobs in parallel using multiprocessing? (ENTER/n) ')
			if rsp == '':
				inputs = range(njobs)
				num_cores = multiprocessing.cpu_count()
				print 'NOTE: Running feat in parallel across %s cores now...\n'%(num_cores)
				results = Parallel(n_jobs=num_cores)(delayed(call_feat_job)(i,jobsdict,level) for i in inputs)
			else:
				print "NOTE: Running commands serially now...\n"
				for i in range(njobs):
					call_feat_job(i,jobsdict,level)

if __name__ == '__main__':
	main()