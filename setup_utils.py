"""
Functions for interacting with model_params, condition_key, and task_contrasts
"""

# Created by Alice Xue, 06/2018

import copy
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

"""
Creates subject and onset directories within level 1 model directory 
"""
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

"""
Creates model_params.json if not found with default parameters
specificruns is set to all possible runs
"""
def create_level1_model_params_json(studyid,basedir,modelname):
	# Creates model_params.json file to define arguments 
	# Keys must be spelled correctly

	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)
	subs=study_info.keys()

	params={'studyid':studyid,'basedir':basedir,'specificruns':study_info,'smoothing':0,'use_inplane':0,'nonlinear':False,'nohpf':True,'nowhiten':True,'noconfound':True,'modelname':modelname,'anatimg':'','doreg':False,'spacetag':'','altBETmask':False}
	modeldir=os.path.join(basedir,studyid,'model','level1','model-%s'%modelname)
	if not os.path.exists(modeldir):
		os.makedirs(modeldir)
				
	if not os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','w') as outfile:
			json.dump(params,outfile)
		print "Created sample model_params.json with default values"
	else:
		print "Found existing model_params.json"

"""
Creates empty condition_key.json if not found
"""
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

"""
Creates empty task_contrasts.json if not found
"""
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

"""
Modifies model_param.json based on user input
"""
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
				if isinstance(cur_val,dict):
					pprint_val=json.dumps(cur_val)
				else:
					pprint_val=cur_val
				if (isinstance(cur_val,str) or isinstance(cur_val,unicode)) and len(cur_val) == 0:
					pprint_val='\"\"'
				print '\n', param+':', pprint_val
				rsp=None
				while rsp != 'y' and rsp != '':
					rsp=raw_input('Do you want to change %s? (y/ENTER) '%(param))
				if rsp == 'y':
					if isinstance(cur_val,bool): # if it's a boolean, just reverse it 
						new_params[param] = not cur_val
					else:
						if param == 'specificruns': # this is a dictionary/json object
							new_params[param]=input_to_modify_specificruns(studyid,basedir,params[param])
							"""
							validinput=False
							while not validinput:
								try:

									new_param_val=raw_input('New value of %s: '%param)
									new_params[param]=json.loads(new_param_val)
									validinput=True
								except:
									print "Invalid value for specificruns. Must be able to call json.loads on the input."
									print ""Example: {"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}""
							"""
						else:
							validinput=False
							while not validinput:
								new_param_val=raw_input('New value of %s: '%param)
								if isinstance(cur_val,int): 
									try: # make sure input is integer 
									    new_param_val=int(new_param_val)
									    new_params[param]=new_param_val
									    validinput=True
									except ValueError:
									    validinput=False
								else:
									new_params[param]=new_param_val
									validinput=True

					if isinstance(cur_val,dict):
						print '%s changed to %s'%(param,json.dumps(new_params[param]))
					else:
						pprint_val = new_params[param]
						if (isinstance(pprint_val,str) or isinstance(pprint_val,unicode)) and len(pprint_val) == 0:
							pprint_val='\"\"'
						print '%s changed to %s'%(param,pprint_val)
				else:
					new_params[param]=params[param]
	with open(modeldir+'/model_params.json','w') as outfile:
		json.dump(new_params,outfile)
		print '\nUpdated %s.'%(modeldir+'/model_params.json')
		for param in ['modelname']+ordered_params:
			if isinstance(new_params[param],dict):
				pprint_val=json.dumps(new_params[param])
			else:
				pprint_val=new_params[param]
			if (isinstance(pprint_val,str) or isinstance(pprint_val,unicode)) and len(pprint_val) == 0:
				pprint_val='\"\"'
			print param+':', pprint_val

"""
Modifies specificruns based on user input 
Prints instructions for modifying specificruns
If parameter specificruns is empty, will retrieve all runs and set specificruns to that
"""
def input_to_modify_specificruns(studyid,basedir,specificruns):
	if len(specificruns) == 0:
		hasSessions=False
		studydir=os.path.join(basedir,studyid)
		study_info=get_study_info(studydir,hasSessions)
		if len(study_info.keys()) > 0:
			if not study_info[study_info.keys()[0]]: # if empty
				hasSessions=True
				study_info=get_study_info(studydir,hasSessions)
		subs=study_info.keys()
		print 'Here are all of the runs in %s:'%(os.path.join(basedir,studyid,'fmriprep'))
		print '\n',json.dumps(study_info),'\n'

		specificruns = study_info

	print 'Four entities exist in the BIDS specification: subject (sub-), session (ses-), task (task-), and run (run-)'
	print 'To exclude all instances of a sub|ses|task|run, enter the full name of the sub|ses|task|run to exclude (including the tag in the beginning)'
	print '\t(e.g. sub-01)'
	print 'To exclude a specific ses|task|run, enter each entity separated by forward slashes.'
	print 'The entities must be in descending order, where sub > ses > task > run'
	print '\t(e.g. sub-01/ses-01/task-flanker/run-2 (to exclude this specific run))'
	print '\t(e.g. sub-02/ses-01/task-flanker (to exclude this specific task for this subject))'
	print 'Use commas to separate multiple exclusion criteria or enter each criteria one by one and press ENTER when you are finished modifying specificruns'
	print '\t(e.g. sub-02,sub-01/ses-01/task-flanker)'
	print 'Note: In the specificruns object, the tags task- and run- are omitted for better readability.'
	
	continueAsking = True
	while continueAsking:
		items_to_exclude=raw_input('Exclude the following: ')
		if items_to_exclude == '':
			continueAsking = False
		else:
			items_to_exclude_list = items_to_exclude.split(',')
			for i in range(0,len(items_to_exclude_list)):
				items_to_exclude_list[i] = items_to_exclude_list[i].strip() # remove any trailing/leading whitespace
			for item in items_to_exclude_list:
				if '/' in item:
					specificruns=remove_specific_items_from_study_info(item,specificruns)
				else:
					specificruns=remove_from_study_info(item,specificruns)
		print 'New specificruns: ', json.dumps(specificruns)
	return specificruns

"""
item: string that starts with "sub-", "ses-", "task-", or "run-"
"""
def remove_from_study_info(item,specificruns):
	try:
		assert specificruns.values()[0].keys()[0].startswith('ses-')
		hasSessions = True
	except:
		hasSessions = False
	if item.startswith("sub-") or item.startswith("ses-") or item.startswith("task-") or item.startswith("run-"):
		study_info=specificruns
		study_info_copy=copy.deepcopy(study_info)
		new_specificruns={}
		subs=study_info.keys()
		if item.startswith('sub-') and item in subs:
			del study_info_copy[item] 
		# iterate through each subject, session, task, and runs
		for subid in subs:
			sub=subid[len('sub-'):] # sub is the subject ID without the prefix 'sub-'
			if hasSessions:
				sessions=study_info[subid].keys()
				if item.startswith('ses-') and item in sessions:
					del study_info_copy[subid][item]
					if len(study_info_copy[subid]) == 0:
						del study_info_copy[subid]
				for ses in sessions:
					sesname=ses[len('ses-'):]
					tasks=study_info[subid][ses].keys()
					if item.startswith('task-') and item[len('task-'):] in tasks:
						del study_info_copy[subid][ses][item[len('task-'):]]
						if len(study_info_copy[subid][ses]) == 0:
								del study_info_copy[subid][ses]
					for task in tasks:
						runs=study_info[subid][ses][task]
						if item.startswith('run-') and item[len('run-'):] in runs:
							study_info_copy[subid][ses][task].remove(item[len('run-'):])
							if len(study_info_copy[subid][ses][task]) == 0:
								del study_info_copy[subid][ses][task]
			else: # no sessions
				tasks=study_info[subid].keys()
				if item.startswith('task-') and item[len('task-'):] in tasks:
					del study_info_copy[subid][item[len('task-'):]]
					if len(study_info_copy[subid]) == 0:
							del study_info_copy[subid]
				list.sort(tasks)
				for task in tasks:
					runs=study_info[subid][task]
					if item.startswith('run-') and item[len('run-'):] in runs:
						study_info_copy[subid][task].remove(item[len('run-'):])
						if len(study_info_copy[subid][task]) == 0:
							del study_info_copy[subid][task]

		return study_info_copy
	else:
		print 'ERROR: Invalid item to remove. Must start with "sub-", "ses-", "task-", or "run-"'
		return specificruns

"""
items: string with sub/ses/task/run separated by forward slashes. Each item start with the appropriate tag ("sub-","ses-",...)
specificruns: nested dictionary that details each sub, ses, task, run
"""
def remove_specific_items_from_study_info(items,study_info):
	specificruns=copy.deepcopy(study_info)
	item_values = {'sub-':0,'ses-':1,'task-':2,'run-':3}
	curr_value = -1
	item_list = items.split('/')
	parsed_item_list=[]
	valid = True
	correctOrder = True
	for item in item_list:
		if item.startswith("sub-") or item.startswith("ses-") or item.startswith("task-") or item.startswith("run-"):
			head_tag = item[:item.find('-')+1]
			if head_tag in item_values:
				if item_values[head_tag] > curr_value:
					curr_value = item_values[head_tag]
					if item.startswith("task-"):
						parsed_item_list.append(item[len('task-'):])
					elif item.startswith("run-"):
						parsed_item_list.append(item[len('run-'):])
					else:
						parsed_item_list.append(item)
				else:
					correctOrder = False
		else:
			if item!='': # if there's an empty value
				valid = False
	if correctOrder and valid:
		if check_for_item_in_study_info(specificruns,parsed_item_list,0):
			return delete_specific_item_in_study_info(specificruns,parsed_item_list,0)
		else:
			print 'ERROR: Specified items not found.'
	if not valid:
		print 'ERROR: Invalid format.'
	if not correctOrder:
		print 'ERROR: Incorrect order'
	return specificruns

"""
Recursive function that deletes a ses/task/run specified by item_list from the nested dictionary specificruns
specificruns: nested dictionary that details each sub, ses, task, run
item_list: list of nested keys that should be in specificruns
items_index: int that keeps track of current item in item_list that is being searched
Returns specificruns with the item in item_list removed
"""
def delete_specific_item_in_study_info(specificruns,item_list,items_index):
	if items_index < len(item_list)-1:
		item = item_list[items_index]
		if item in specificruns.keys():
			new_items = delete_specific_item_in_study_info(specificruns[item],item_list,items_index+1) # iterate through recursive dictionary
			if len(new_items) > 0:
				specificruns[item] = new_items
			else:
				del specificruns[item]
			return specificruns
	elif items_index == len(item_list)-1: # reached last item in item_list, which should be removed
		item = item_list[items_index]
		if isinstance(specificruns,dict):
			if item in specificruns.keys():
				del specificruns[item]
				return specificruns
		elif isinstance(specificruns,list): # runs are a list, not dictionary
			if item in specificruns:
				specificruns.remove(item)
				return specificruns
	return specificruns

"""
Recursive function that looks for each item in item_list in the nested dictionary specificruns
specificruns: nested dictionary that details each sub, ses, task, run
item_list: list of nested keys that should be in specificruns
items_index: int that keeps track of current item in item_list that is being searched
Returns True if item_list is a list of nested keys in specificruns
"""
def check_for_item_in_study_info(specificruns,item_list,items_index):
	if items_index < len(item_list)-1:
		item = item_list[items_index]
		if item in specificruns.keys():
			return check_for_item_in_study_info(specificruns[item],item_list,items_index+1)
	elif items_index == len(item_list)-1: # reached last item in item_list
		item = item_list[items_index]
		if isinstance(specificruns,dict):
			if item in specificruns.keys():
				return True
		elif isinstance(specificruns,list): # runs are a list, not dictionary
			if item in specificruns:
				return True
	return False
