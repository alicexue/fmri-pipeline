"""
Generates run_level3_feat.sbatch to run mk_all_level3_fsf in a job array
Runs the generated sbatch file
"""

# Created by Alice Xue, 06/2018

import mk_all_level3_fsf
import subprocess
import sys
import argparse
import json

def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='setup_jobs')
    #parser.add_argument('integers', metavar='N', type=int, nargs='+',help='an integer for the accumulator')
    # set up boolean flags

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
    parser.add_argument('--modelnum', dest='modelnum',type=int,
        default=1,help='Model number')
    parser.add_argument('--subs', dest='subids', nargs='+',
        default=[],help='subject identifiers (not including prefix "sub-")')

    args = parser.parse_args(argv)
    return args

def main(argv=None):
	args=parse_command_line(argv)
	email=args.email
	account=args.account
	time=args.time
	nodes=args.nodes
	subids=args.subids

	sys_argv=sys.argv[:]

	params_to_remove=['--email','-e','-A','--account','-t','--time','-N','--nodes']
	for param in params_to_remove:
		if param in sys_argv:
			i=sys_argv.index(param)
			del sys_argv[i]
			del sys_argv[i]
	del sys_argv[0]

	print sys_argv

	njobs=len(mk_all_level3_fsf.main(argv=sys_argv[:]))
	commands=['python','mk_all_level3_fsf.py'] + sys_argv
	commands+=['--slurm_array_task_id', '$SLURM_ARRAY_TASK_ID']
	strcommand =' '.join(c for c in commands)
	with open('run_level3.sbatch', 'w') as qsubfile:
		qsubfile.write('#!/bin/sh\n')
		qsubfile.write('#\n')
		qsubfile.write('#SBATCH -J run_level3_feat\n')
		qsubfile.write('#SBATCH -A %s\n'%(account))
		qsubfile.write('#SBATCH -N %d\n'%(nodes))
		qsubfile.write('#SBATCH -c 1\n')
		qsubfile.write('#SBATCH --time=%s\n'%(time))
		qsubfile.write('#SBATCH --mail-user=%s\n'%(email))
		qsubfile.write('#SBATCH --mail-type=ALL\n')
		qsubfile.write('#SBATCH --array=%s-%s\n'%(0,njobs-1))
		qsubfile.write('#----------------\n')
		qsubfile.write('# Job Submission\n')
		qsubfile.write('#----------------\n')
		qsubfile.write(strcommand)
	try:
		subprocess.call(['sbatch','run_level3.sbatch'])
	except:
		print "\nsbatch command was not found. Are you sure you're running this program on a cluster?"
		print "WARNING: Running commands serially now...\n"
		for i in range(njobs):
			subprocess.call(commands[:-2]+['--slurm_array_task_id',str(i)])


if __name__ == '__main__':
    main()