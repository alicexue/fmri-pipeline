import json
import os
import sys
from argparse import Namespace

def model_params_json_to_namespace(studyid,basedir,modelnum):
	# Converts json of parameters to Namespace
	modeldir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum)
	if os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','r') as f:
			params = json.load(f)
		args=Namespace()
		args.modelnum=params['modelnum']
		args.specificruns=params['specificruns']
		args.studyid=params['studyid']
		args.basedir=params['basedir']
		args.anatimg=params['anatimg']
		args.hpf=params['nohpf']
		args.use_inplane=params['use_inplane']
		args.whiten=params['nowhiten']
		args.nonlinear=params['nonlinear']
		args.altBETmask=params['altBETmask']
		args.smoothing=params['smoothing']
		args.doreg=params['doreg']
		args.confound=params['noconfound'] # args.confound instead of noconfound bc of dest 
		args.spacetag=params['spacetag']
		return args
	else:
		print "model_params.json does not exist in %s"%modeldir

def model_params_json_to_list(studyid,basedir,modelnum):
	# Takes json of argument parameters and converts to string of commands
	modeldir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum)
	if os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','r') as f:
			params = json.load(f)
		
		# no_action_params: parameters that don't have store_true or store_false as an action
		no_action_params=['studyid','basedir','smoothing','use_inplane','modelnum','anatimg','spacetag']
		action_params={'nonlinear':False,'nohpf':True,'nowhiten':True,'noconfound':True,'doreg':False,'altBETmask':False}
		# keys in action_params are arguments that have action that stores parameter as true/false
		# values in action_params are default arguments
		args=[]
		for p in no_action_params:
			args.append('--'+p)
			args.append(str(params[p]))

		for p in action_params.keys():
			if params[p] != action_params[p]: # if the passed parameter is not the same as the default value
				args.append('--'+p)
		return args
	else:
		print "model_params.json does not exist in %s"%modeldir
		sys.exit(-1)