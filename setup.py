import json
import os
import sys
from directory_struct_utils import *

def create_model_level1_dir(studyid,basedir,modelnum):
	hasSessions=False
	studydir=os.path.join(basedir,studyid)
	study_info=get_study_info(studydir,hasSessions)
	if len(study_info.keys()) > 0:
		if not study_info[study_info.keys()[0]]: # if empty
			hasSessions=True
			study_info=get_study_info(studydir,hasSessions)
	subs=study_info.keys()
	print study_info
	list.sort(subs)
	i=0
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
						onsetsdir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum,subid,ses,'task-%s_run-%s'%(task,run),'onsets')
						if not os.path.exists(onsetsdir):
							os.makedirs(onsetsdir)
						evfilename=onsetsdir+'/%s_%s_task-%s_run-%s_ev-%03d'%(subid,ses,task,run,1)
						if not os.path.exists(evfilename+'.tsv') and not os.path.exists(evfilename+'.txt'):
							with open(evfilename+'.tsv','a') as outfile:
								outfile.write('')
								i+=1
		else:
			tasks=study_info[subid].keys()
			list.sort(tasks)
			for task in tasks:
				runs=study_info[subid][task]
				list.sort(runs)
				for run in runs:
					onsetsdir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum,subid,'task-%s_run-%s'%(task,run),'onsets')
					if not os.path.exists(onsetsdir):
						os.makedirs(onsetsdir)
					evfilename=onsetsdir+'/%s_task-%s_run-%s_ev-%03d'%(subid,task,run,1)
					if not os.path.exists(evfilename+'.tsv') and not os.path.exists(evfilename+'.txt'):
						with open(evfilename+'.tsv','a') as outfile:
							outfile.write('')
							i+=1
	print "Created %d onset directories and empty sample ev files"%(i)



def create_level1_model_params_json(studyid,basedir,modelnum):
	# Creates model_params.json file to define arguments 
	# Keys must be spelled correctly
	params={'studyid':studyid,'basedir':basedir,'specificruns':{},'smoothing':0,'use_inplane':0,'nonlinear':False,'nohpf':True,'nowhiten':True,'noconfound':True,'modelnum':modelnum,'anatimg':'','doreg':False,'spacetag':'','altBETmask':False}
	modeldir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum)
	if not os.path.exists(modeldir):
		os.makedirs(modeldir)
				
	if not os.path.exists(modeldir+'/model_params.json'):
		with open(modeldir+'/model_params.json','w') as outfile:
			json.dump(params,outfile)
		print "Created sample model_params.json with default values"

def create_empty_condition_key(studyid,basedir,modelnum):
	modeldir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum)
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

def create_empty_task_contrasts_file(studyid,basedir,modelnum):
	modeldir=os.path.join(basedir,studyid,'model','level1','model%03d'%modelnum)
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

def main():
	if len(sys.argv) < 4:
		print "usage: setup.py <studyid> <basedir> <modelnum>"
		sys.exit(-1)
	studyid=sys.argv[1]
	basedir=sys.argv[2]
	modelnum=int(sys.argv[3])
	create_level1_model_params_json(studyid,basedir,modelnum)
	create_model_level1_dir(studyid,basedir,modelnum)
	create_empty_condition_key(studyid,basedir,modelnum)
	create_empty_task_contrasts_file(studyid,basedir,modelnum)

if __name__ == '__main__':
	main()