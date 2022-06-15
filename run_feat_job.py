"""Calls mk_level1_fsf_bbr, mk_level2_fsf, mk_level3_fsf to create a particular fsf or call feat The feat created is
determined by the parameters in jobs[i], where jobs is a dictionary and i is the key of the job to run """

# Created by Alice Xue, 06/2018

import argparse
import json
import subprocess
import sys

import mk_level1_fsf_bbr
import mk_level2_fsf


def parse_command_line(argv):
    parser = argparse.ArgumentParser(description='get_jobs')
    parser.add_argument('--jobs', dest='jobs', type=json.loads,
                        required=True,
                        help='JSON object in a string where the keys are indices for slurm job arrays and keys are the '
                             'jobs to run in a subprocess.')
    parser.add_argument('-i', '--jobtorun', dest='i',
                        required=True, help='Key (index) of job to run')
    parser.add_argument('--level', dest='level', type=int,
                        required=True, help='Analysis of level')
    args = parser.parse_args(argv)
    return args


def main():
    args = parse_command_line(argv=None)
    jobs = args.jobs
    i = args.i
    level = args.level

    if level not in [1, 2, 3]:
        print("%d is an invalid level of analysis" % level)
        sys.exit(-1)

    if i in jobs.keys():
        if level == 1:
            mk_level1_fsf_bbr.main(argv=jobs[i])  # create fsf
        elif level == 2:
            mk_level2_fsf.main(argv=jobs[i])  # create fsf
        elif level == 3:
            args = ['feat', jobs[i]]
            print('Calling', ' '.join(args))  # call feat on fsf's specified in jobs
            # the fsf's were created in run_level3 when mk_all_level3_fsf was called
            subprocess.call(args)
    else:
        print("%d is not a key in the jobs dictionary: %s" % i)
        sys.exit(-1)


if __name__ == '__main__':
    main()
