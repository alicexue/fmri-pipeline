"""
Functions for interacting with model_params, condition_key, and task_contrasts
"""

# Created by Alice Xue, 06/2018

import json
import os
import sys
from argparse import Namespace
from directory_struct_utils import *

def model_params_json_to_namespace(studyid,basedir,modelname):
	# Converts json of parameters to Namespace object that can be parsed
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','r') as f:
			params = json.load(f)
		args=Namespace()
		args.modelname=params['modelname']
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
		print "ERROR: model_params.json does not exist in %s"%modeldir
		sys.exit(-1)

def model_params_json_to_list(studyid,basedir,modelname):
	# Takes json of argument parameters and converts to string of commands, which can be called on in a subprocess
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','r') as f:
			params = json.load(f)
		
		# no_action_params: parameters that don't have store_true or store_false as an action
		no_action_params=['studyid','basedir','smoothing','use_inplane','modelname','anatimg','spacetag']
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

def create_model_level1_dir(studyid,basedir,modelname):
	# Creates model dir, the subject dirs, onset dirs
	# no longer creates empty EV files - causes fsl errors if not removed by user
	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)
	subs=study_info.keys()
	print json.dumps(study_info)
	list.sort(subs)
	i=0
	# iterate through the subjects, sessions, tasks, and runs
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
						onsetsdir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname,subid,ses,'task-%s_run-%s'%(task,run),'onsets')
						if not os.path.exists(onsetsdir):
							os.makedirs(onsetsdir)
						"""
						evfilename=onsetsdir+'/%s_%s_task-%s_run-%s_ev-%03d'%(subid,ses,task,run,1)
						if not os.path.exists(evfilename+'.tsv') and not os.path.exists(evfilename+'.txt'):
							with open(evfilename+'.tsv','a') as outfile:
								outfile.write('')
						"""
						i+=1
		else:
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				for run in runs:
					onsetsdir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname,subid,'task-%s_run-%s'%(task,run),'onsets')
					if not os.path.exists(onsetsdir):
						os.makedirs(onsetsdir)
					evfilename=onsetsdir+'/%s_task-%s_run-%s_ev-%03d'%(subid,task,run,1)
					"""
					if not os.path.exists(evfilename+'.tsv') and not os.path.exists(evfilename+'.txt'):
						with open(evfilename+'.tsv','a') as outfile:
							outfile.write('')
					"""
					i+=1
	#print "Created %d onset directories and empty sample ev files"%(i)
	print "Created %d onset directories"%(i)
	return hasSessions

def create_level1_model_params_json(studyid,basedir,modelname):
	# Creates model_params.json file to define arguments 
	# Keys must be spelled correctly
	params={'studyid':studyid,'basedir':basedir,'specificruns':{},'smoothing':0,'use_inplane':0,'nonlinear':False,'nohpf':True,'nowhiten':True,'noconfound':True,'modelname':modelname,'anatimg':'','doreg':False,'spacetag':'','altBETmask':False}
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if not os.path.exists(modeldir):
		os.makedirs(modeldir)
				
	if not os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','w') as outfile:
			json.dump(params,outfile)
		print "Created sample model_params.json with default values"
	else:
		print "Found existing model_params.json"

def create_empty_condition_key(studyid,basedir,modelname):
	# Creates an empty sample condition key 
	# Gets the name of all possible tasks (that the first subject did), and adds those to the condition key
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if not os.path.exists(modeldir):
		os.makedirs(modeldir)

	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)
	all_tasks=[]
	subs=study_info.keys()
	list.sort(subs)
	i=0
	subid=subs[0]
	sub=subid[len('sub-'):]
	if hasSessions:
		sessions=study_info[subid].keys()
		list.sort(sessions)
		for ses in sessions:
			sesname=ses[len('ses-'):]
			tasks=study_info[subid][ses].keys()
			list.sort(tasks)
			all_tasks=tasks
	else:
		tasks=study_info[subid].keys()
		list.sort(tasks)
		all_tasks=tasks

	if not os.path.exists(modeldir+'/condition_key.json'):
		with open(modeldir+'/condition_key.json','w') as outfile:
			condition_key={}
			for task in all_tasks:
				condition_key[task]={"1":""}
			json.dump(condition_key,outfile)
		print "Created empty condition_key.json"
	else:
		print "Found existing condition_key.json"

def create_empty_task_contrasts_file(studyid,basedir,modelname):
	# Creates an empty task_contrasts file with the task names as keys
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if not os.path.exists(modeldir):
		os.makedirs(modeldir)

	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)
	all_tasks=[]
	subs=study_info.keys()
	list.sort(subs)
	i=0
	subid=subs[0]
	sub=subid[len('sub-'):]
	if hasSessions:
		sessions=study_info[subid].keys()
		list.sort(sessions)
		for ses in sessions:
			sesname=ses[len('ses-'):]
			tasks=study_info[subid][ses].keys()
			list.sort(tasks)
			all_tasks=tasks
	else:
		tasks=study_info[subid].keys()
		list.sort(tasks)
		all_tasks=tasks

	if not os.path.exists(modeldir+'/task_contrasts.json'):
		with open(modeldir+'/task_contrasts.json','w') as outfile:
			condition_key={}
			for task in all_tasks:
				condition_key[task]={"1":[0,0,0]}
			json.dump(condition_key,outfile)
		print "Created empty task_contrasts.json"
	else:
		print "Found existing task_contrasts.json"

def check_model_params_cli(studyid,basedir,modelname):
	# Modifies model_params by interacting with user through the command line
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	new_params={}
	if os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','r') as f:
			params = json.load(f)
			new_params['modelname']=params['modelname']
			# not including modelname
			ordered_params=['studyid','basedir','specificruns','anatimg','nohpf','use_inplane','nowhiten','nonlinear','altBETmask','smoothing','doreg','noconfound','spacetag']
			
			for param in ordered_params:
				cur_val=params[param]
				if type(cur_val) == dict:
					pprint_val=json.dumps(cur_val)
				else:
					pprint_val=cur_val
				if ((type(cur_val) == str) or (type(cur_val) == unicode)) and len(cur_val) == 0:
					pprint_val='\"\"'
				print '\n', param+':', pprint_val
				rsp=None
				while rsp != 'y' and rsp != '':
					rsp=raw_input('Do you want to change %s? (y/ENTER) '%(param))
				if rsp == 'y':
					if type(cur_val) == bool: # if it's a boolean, just reverse it 
						new_params[param] = not cur_val
					else:
						if param == 'specificruns': # this is a dictionary/json object
							validinput=False
							while not validinput:
								try:
									new_param_val=raw_input('New value of %s: '%param)
									new_params[param]=json.loads(new_param_val)
									validinput=True
								except:
									print "Invalid value for specificruns. Must be able to call json.loads on the input."
									print """Example: {"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}"""
						else:
							validinput=False
							while not validinput:
								new_param_val=raw_input('New value of %s: '%param)
								if type(cur_val) == int: 
									try: # make sure input is integer 
									    new_param_val=int(new_param_val)
									    new_params[param]=new_param_val
									    validinput=True
									except ValueError:
									    validinput=False
								else:
									new_params[param]=new_param_val
									validinput=True

					if type(cur_val) == dict:
						print '%s changed to %s'%(param,json.dumps(new_params[param]))
					else:
						pprint_val = new_params[param]
						if ((type(pprint_val) == str) or (type(pprint_val) == unicode)) and (len(pprint_val) == 0):
							pprint_val='\"\"'
						print '%s changed to %s'%(param,pprint_val)
				else:
					new_params[param]=params[param]
	with open(modeldir+'/model_params.json','w') as outfile:
		json.dump(new_params,outfile)
		print '\nUpdated %s.'%(modeldir+'/model_params.json')
		for param in ['modelname']+ordered_params:
			if type(new_params[param]) == dict:
				pprint_val=json.dumps(new_params[param])
			else:
				pprint_val=new_params[param]
			if ((type(pprint_val) == str) or (type(pprint_val) == unicode)) and (len(pprint_val) == 0):
				pprint_val='\"\"'
			print param+':', pprint_val