import sys
import argparse
import json
import mk_level1_fsf_bbr

def parse_command_line(argv):
	parser = argparse.ArgumentParser(description='get_jobs')
	parser.add_argument('--jobs',dest='jobs',type=json.loads,
		required=True, help='JSON object in a string where the keys are indices for slurm job arrays and keys are the jobs to run in a subprocess.')
	parser.add_argument('-i','--jobtorun',dest='i',
		required=True, help='key of job to run')
	args=parser.parse_args(argv)
	return args

def main():
	args=parse_command_line(argv=None)
	jobs=args.jobs
	i=args.i
	if i in jobs.keys():
		mk_level1_fsf_bbr.main(argv=jobs[i])
	else:
		print "Could not find %d as a key in the jobs dictionary: %s"%i
		sys.exit(-1)
	

if __name__ == '__main__':
	main()
