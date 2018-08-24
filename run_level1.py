#!/usr/bin/env python
"""
Generates run_level1.sbatch to run mk_all_level1_fsf_bbr in a job array
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

import get_level1_jobs
import setup_utils

def parse_command_line(argv):
	parser = argparse.ArgumentParser(description='setup_jobs')

	parser.add_argument('-e','--email',dest='email',
		required=True,help='Email to send job updates to')
	parser.add_argument('-A','--account',dest='account',
		required=True,help='Slurm account')
	parser.add_argument('-t', '--time',dest='time',
		default="02:00:00",help='Estimated time to run each job - hh:mm:ss')
	parser.add_argument('-N', '--nodes',dest='nodes',type=int,
		default=1,help='Number of nodes')
	parser.add_argument('--nofeat',dest='nofeat',action='store_true',
		default=False,help='Only create the fsf\'s, don\'t call feat')
	
	parser.add_argument('--studyid', dest='studyid',
		required=True,help='Study ID')
	parser.add_argument('--basedir', dest='basedir',
		required=True,help='Base directory (above studyid directory)')
	parser.add_argument('-m', '--modelname', dest='modelname',
		required=True,help='Model name')

	parser.add_argument('-s', '--specificruns', dest='specificruns', type=json.loads,
		default={},help="""
			JSON object in a string that details which runs to create fsf's for. If specified, ignores specificruns specified in model_params.json.
			Ex: If there are sessions: \'{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}\' where flanker is a task name and ["1", "2"] is a list of the runs.
			If there aren't sessions: \'{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}\'. Make sure this describes the fmriprep folder, which should be in BIDS format.
			Make sure to have single quotes around the JSON object and double quotes within."""
			)

	args = parser.parse_args(argv)
	return args

def call_feat_job(i,jobsdict,level):
	subprocess.call(['python', 'run_feat_job.py', '--jobs', '%s'%json.dumps(jobsdict),'-i',str(i), '--level', str(level)])

def main(argv=None):
	level=1
	d=datetime.datetime.now()
	args=parse_command_line(argv)

	email=args.email
	account=args.account
	time=args.time
	nodes=args.nodes
	studyid=args.studyid
	basedir=args.basedir
	modelname=args.modelname
	specificruns=args.specificruns
	nofeat=args.nofeat

	# double checks with user that all files have been set
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	rsp=None
	print 'Make sure that the following have been set:'
	print '\t%s/model_params.json'%modeldir
	print '\t%s/condition_key.json'%modeldir
	print '\t%s/task_contrasts.json (optional but must be removed if not using)'%modeldir
	print '\t%s/design_level1_custom.stub (optional)'%modeldir
	print '\tEV files under the onset directories'
	while rsp != '':
		rsp=raw_input('Press ENTER to continue:')	
	
	# get specificruns from model_params
	args=setup_utils.model_params_json_to_namespace(studyid,basedir,modelname) 
	if specificruns == {}: # if specificruns from sys.argv is empty (default), use specificruns from model_param
		specificruns=args.specificruns

	# get the list of jobs to run
	jobs=get_level1_jobs.get_level1_jobs(studyid,basedir,modelname,specificruns,specificruns,nofeat) 
	njobs=len(jobs)
	# turn the list of jobs into a dictionary with the index as the key
	jobsdict={}
	for i in range(0,njobs):
		jobsdict[i]=jobs[i]

	if nofeat:
		for i in range(njobs):
			call_feat_job(i,jobsdict,level)
		print '\n%s *.fsf files created.'%(njobs)
	else:
		print "WARNING: If any feat files exist (warnings would be printed above), they will not be overwritten if you continue."
		rsp=None
		while rsp != '':
			rsp=raw_input('Press ENTER to continue:')

		# create an sbatch file to run the job array
		j='level1-feat'
		with open('run_level1.sbatch', 'w') as qsubfile:
			qsubfile.write('#!/bin/sh\n')
			qsubfile.write('#\n')
			qsubfile.write('#SBATCH -J %s\n'%(j))
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
			qsubfile.write("python run_feat_job.py --jobs '%s' -i $SLURM_ARRAY_TASK_ID --level 1"%json.dumps(jobsdict))

		try:
			subprocess.call(['sbatch','run_level1.sbatch'])
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
