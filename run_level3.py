#!/usr/bin/env python
"""
Runs mk_all_level3_fsf to create fsf's 
Generates run_level3_feat.sbatch and runs run_feat_job in job array and call feat on the created fsf's
Runs the generated sbatch file
"""

# Created by Alice Xue, 06/2018

import argparse
import datetime
import inspect
from joblib import Parallel, delayed
import json
import multiprocessing
import os
import shutil
import subprocess
import sys

import mk_all_level3_fsf


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='setup_jobs')

    parser.add_argument('-e', '--email', dest='email',
                        required=True, help='Email to send job updates to')
    parser.add_argument('-A', '--account', dest='account',
                        required=True, help='Slurm account')
    parser.add_argument('-t', '--time', dest='time',
                        default="00:30:00", help='Estimated time to run each job - hh:mm:ss')
    parser.add_argument('-N', '--nodes', dest='nodes', type=int,
                        default=1, help='Number of nodes')
    parser.add_argument('-M', '--mem', dest='mem', type=int,
                        default=1024, help='Memory allocation in MB. Defaults to 1024 MB.')
    parser.add_argument('--studyid', dest='studyid',
                        required=True, help='Study ID')
    parser.add_argument('--basedir', dest='basedir',
                        required=True, help='Base directory (above studyid directory)')
    parser.add_argument('--outdir', dest='outdir',
                        default="", help='Full path of directory where sbatch output should be saved')
    parser.add_argument('-m', '--modelname', dest='modelname',
                        required=True, help='Model name')
    parser.add_argument('--subs', dest='subids', nargs='+',
                        default=[], help='subject identifiers (not including prefix "sub-")')
    parser.add_argument('--randomise', dest='randomise', action='store_true',
                        default=False, help='Use Randomise for stats instead of FLAME 1')
    parser.add_argument('--nofeat', dest='nofeat', action='store_true',
                        default=False, help='Only create the fsf\'s, don\'t call feat')

    args = parser.parse_args(argv)
    return args


def call_feat_job(i, jobsdict, level):
    fmripipelinedir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    subprocess.call(
        ['python', os.path.join(fmripipelinedir, 'run_feat_job.py'), '--jobs', '%s' % json.dumps(jobsdict), '-i',
         str(i), '--level', str(level)])


def main(argv=None):
    level = 3
    d = datetime.datetime.now()

    args = parse_command_line(argv)
    studyid = args.studyid
    basedir = args.basedir
    email = args.email
    account = args.account
    time = args.time
    nodes = args.nodes
    mem = args.mem
    subids = args.subids
    nofeat = args.nofeat
    outdir = args.outdir

    studydir = os.path.join(basedir, studyid)

    sys_argv = sys.argv[:]

    # remove arguments that mk_all_level3_fsf.py doesn't take
    params_to_remove = ['--email', '-e', '-A', '--account', '-t', '--time', '-N', '--nodes', '--outdir', '-M', '--mem']
    for param in params_to_remove:
        if param in sys_argv:
            i = sys_argv.index(param)
            del sys_argv[i]
            del sys_argv[i]
    del sys_argv[0]

    print(sys_argv)

    # get the list of jobs to run
    existing_copes, jobs = mk_all_level3_fsf.main(argv=sys_argv[:])

    if len(existing_copes) > 0:
        rsp = None
        while rsp != 'y' and rsp != '':
            rsp = input('Do you want to remove existing gfeat dirs? (y/ENTER) ')
        if rsp == 'y':
            for feat_file in existing_copes:
                print('Removing %s' % feat_file)
                if os.path.exists(feat_file):
                    shutil.rmtree(feat_file)
            existing_copes, jobs = mk_all_level3_fsf.main(argv=sys_argv[:])
            # existing_feat_files should all have been removed
        else:
            print('Not removing feat_files')
            print(
                "WARNING: The existing feat files (see printed warnings above) will not be overwritten if you continue."
            )
        if rsp == 'y':  # wanted to remove feat files
            assert len(
                existing_copes) == 0, 'There are still existing feat files, there was a problem removing those files.'

    njobs = len(jobs)
    # turn the list of jobs into a dictionary with the index as the key
    jobsdict = {}
    for i in range(0, njobs):
        jobsdict[i] = jobs[i]

    if nofeat:
        print('\n%s *.fsf files created.' % njobs)
    else:
        j = 'level3-feat'
        fmripipelinedir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
        # save sbatch output to studydir by default
        if outdir == '':
            homedir = studydir
        else:
            homedir = outdir
            if not os.path.exists(homedir):
                os.makedirs(homedir)
        dateandtime = d.strftime("%d_%B_%Y_%Hh_%Mm_%Ss")
        outputdir = os.path.join(homedir, '%s_%s' % (j, dateandtime))
        if not os.path.exists(outputdir):
            os.mkdir(outputdir)

        # create an sbatch file to run the job array
        sbatch_path = os.path.join(outputdir, 'run_level3.sbatch')
        with open(sbatch_path, 'w') as qsubfile:
            qsubfile.write('#!/bin/sh\n')
            qsubfile.write('#\n')
            qsubfile.write('#SBATCH -J run_level3_feat\n')
            qsubfile.write('#SBATCH -A %s\n' % account)
            qsubfile.write('#SBATCH -N %d\n' % nodes)
            qsubfile.write('#SBATCH -c 1\n')
            qsubfile.write('#SBATCH --time=%s\n' % time)
            qsubfile.write('#SBATCH --mem=%d\n' % mem)
            qsubfile.write('#SBATCH --mail-user=%s\n' % email)
            qsubfile.write('#SBATCH --mail-type=ALL\n')
            qsubfile.write('#SBATCH --array=%s-%s\n' % (0, njobs - 1))
            qsubfile.write('#SBATCH -o %s_%s_%s.o\n' % (os.path.join(outputdir, j), dateandtime, '%a'))
            qsubfile.write('#----------------\n')
            qsubfile.write('# Job Submission\n')
            qsubfile.write('#----------------\n')
            qsubfile.write("python %s --jobs '%s' -i $SLURM_ARRAY_TASK_ID --level 3" % (
                os.path.join(fmripipelinedir, 'run_feat_job.py'), json.dumps(jobsdict)))

        try:
            subprocess.call(['sbatch', sbatch_path])
            print('Saving sbatch output to %s' % outputdir)
        except FileNotFoundError:
            print("\nNOTE: sbatch command was not found.")
            # since not running sbatch, should remove created .sbatch file and outputdir
            os.remove(sbatch_path)
            os.rmdir(outputdir)
            rsp = None
            while rsp != 'n' and rsp != '':
                rsp = input('Do you want to run the jobs in parallel using multiprocessing? (ENTER/n) ')
            if rsp == '':
                inputs = range(njobs)
                num_cores = multiprocessing.cpu_count()
                print('NOTE: Running feat in parallel across %s cores now...\n' % num_cores)
                Parallel(n_jobs=num_cores)(delayed(call_feat_job)(i, jobsdict, level) for i in inputs)
            else:
                print("NOTE: Running commands serially now...\n")
                for i in range(njobs):
                    call_feat_job(i, jobsdict, level)


if __name__ == '__main__':
    main()
