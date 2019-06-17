#!/usr/bin/env python
"""
Generates run_level1.sbatch to run mk_all_level1_fsf_bbr in a job array
Runs the generated sbatch file
"""

# Created by Alice Xue, 06/2018

import argparse
import datetime
from joblib import Parallel, delayed
import inspect
import json
import multiprocessing
import os
import shutil
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
	parser.add_argument('-M', '--mem',dest='mem',type=int,
		default=1024,help='Memory allocation in MB. Defaults to 1024 MB.')
	parser.add_argument('--nofeat',dest='nofeat',action='store_true',
		default=False,help='Only create the fsf\'s, don\'t call feat')
	parser.add_argument('--studyid', dest='studyid',
		required=True,help='Study ID')
	parser.add_argument('--basedir', dest='basedir',
		required=True,help='Base directory (above studyid directory)')
	parser.add_argument('--outdir', dest='outdir',
		default="",help='Full path of directory where sbatch output should be saved')
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
	fmripipelinedir=os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
	subprocess.call(['python',os.path.join(fmripipelinedir,'run_feat_job.py'), '--jobs', '%s'%json.dumps(jobsdict),'-i',str(i), '--level', str(level)])

def main(argv=None):
	level=1
	d=datetime.datetime.now()
	args=parse_command_line(argv)

	email=args.email
	account=args.account
	time=args.time
	nodes=args.nodes
	mem=args.mem
	studyid=args.studyid
	basedir=args.basedir
	modelname=args.modelname
	sys_args_specificruns=args.specificruns
	nofeat=args.nofeat
	outdir=args.outdir

	# double checks with user that all files have been set
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	rsp=None
	print 'Make sure that the following have been set:'
	print '\t%s/model_params.json'%modeldir
	print '\t%s/condition_key.json'%modeldir
	print '\t%s/task_contrasts.json (optional but must be removed if not using)'%modeldir
	print '\t%s/confounds.json (optional but must be removed if not using)'%modeldir
	print '\t%s/design_level1_custom.stub (optional)'%modeldir
	print '\tEV files under the onset directories'
	while rsp != '':
		rsp=raw_input('Press ENTER to continue:')	
	
	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=setup_utils.get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
	setup_utils.generate_confounds_files(studyid,basedir,hasSessions,modelname)

	# get specificruns from model_params
	args=setup_utils.model_params_json_to_namespace(studyid,basedir,modelname) 
	if sys_args_specificruns == {}: # if specificruns from sys.argv is empty (default), use specificruns from model_params
		specificruns=args.specificruns
	else:
		specificruns = sys_args_specificruns

	# get the list of jobs to run
	existing_feat_files, jobs=get_level1_jobs.get_level1_jobs(studyid,basedir,modelname,specificruns,sys_args_specificruns,nofeat) 
	if len(existing_feat_files) > 0: 
		rsp=None
		while rsp!= 'y' and rsp!='':
			rsp=raw_input('Do you want to remove existing feat dirs? (y/ENTER) ')
		if rsp == 'y':
			for feat_file in existing_feat_files:
				print 'Removing %s'%(feat_file)
				if os.path.exists(feat_file):
					shutil.rmtree(feat_file)
			existing_feat_files, jobs=get_level1_jobs.get_level1_jobs(studyid,basedir,modelname,specificruns,sys_args_specificruns,nofeat) 
			# existing_feat_files should all have been removed
		else:
			print 'Not removing feat_files'
			# pass in specificruns both times to ignore existing feat files
			existing_feat_files, jobs=get_level1_jobs.get_level1_jobs(studyid,basedir,modelname,specificruns,specificruns,nofeat) 
	 	if rsp == 'y': # wanted to remove feat files
		 	assert len(existing_feat_files) == 0, 'There are still existing feat files, there was a problem removing those files.'

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
		if len(existing_feat_files) > 0:
			print "WARNING: The existing feat files (see printed warnings above) will not be overwritten if you continue."
		rsp=None
		while rsp != '':
			rsp=raw_input('Press ENTER to continue:')

		j='level1-feat'
		fmripipelinedir=os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
		# save sbatch output to studydir by default
		if outdir == '':
			homedir=studydir
		else:
			homedir=outdir
			if not os.path.exists(homedir):
				os.makedirs(homedir)
		dateandtime=d.strftime("%d_%B_%Y_%Hh_%Mm_%Ss")
		outputdir=os.path.join(homedir,'%s_%s'%(j,dateandtime))
		if not os.path.exists(outputdir):
			os.mkdir(outputdir)

		# create an sbatch file to run the job array
		sbatch_path=os.path.join(outputdir,'run_level1.sbatch')
		with open(sbatch_path, 'w') as qsubfile:
			qsubfile.write('#!/bin/sh\n')
			qsubfile.write('#\n')
			qsubfile.write('#SBATCH -J %s\n'%(j))
			qsubfile.write('#SBATCH -A %s\n'%(account))
			qsubfile.write('#SBATCH -N %d\n'%(nodes))
			qsubfile.write('#SBATCH -c 1\n')
			qsubfile.write('#SBATCH --time=%s\n'%(time))
			qsubfile.write('#SBATCH --mem=%d\n'%(mem))
			qsubfile.write('#SBATCH --mail-user=%s\n'%(email))
			qsubfile.write('#SBATCH --mail-type=ALL\n')
			qsubfile.write('#SBATCH --array=%s-%s\n'%(0,njobs-1))
			qsubfile.write('#SBATCH -o %s_%s_%s.o\n'%(os.path.join(outputdir,j),dateandtime,'%a'))
			qsubfile.write('#----------------\n')
			qsubfile.write('# Job Submission\n')
			qsubfile.write('#----------------\n')
			qsubfile.write("python %s --jobs '%s' -i $SLURM_ARRAY_TASK_ID --level 1"%(os.path.join(fmripipelinedir,'run_feat_job.py'),json.dumps(jobsdict)))

		try:
			subprocess.call(['sbatch',sbatch_path])
			print 'Saving sbatch output to %s'%(outputdir)
		except:
			print "\nNOTE: sbatch command was not found."
			# since not running sbatch, should remove created .sbatch file and outputdir
			os.remove(sbatch_path)
			os.rmdir(outputdir)
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
