# Retrieves fmriprep directory structure

# Created by Alice Xue, 06/2018

import os

# right now checks first subject - doesn't verify all subjects

def get_fmriprep_dir(studydir):
	fmriprep_dir=os.path.join(studydir,'fmriprep')
	if os.path.exists(fmriprep_dir):
		return fmriprep_dir
	else:
		print "fmriprep directory not found in %s"%studydir
		return ''

def get_all_subs(studydir):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=[]
	if os.path.exists(fmriprep):
		folders=os.listdir(fmriprep)
		for folder in folders:
			if os.path.isdir(os.path.join(fmriprep,folder)) and folder.startswith('sub-'):
				i=folder.find('-')
				sub=folder[i+1:]
				all_subs.append(sub)
		list.sort(all_subs)
	return all_subs

def get_runs(funcdir,task):
	runs=[]
	files=os.listdir(funcdir)
	for f in files:
		i1=f.find('_task-'+task+'_run-')+len('_task-'+task+'_run-')
		tmp=f[i1:]
		i2=tmp.find('_')
		run=tmp[:i2]
		if (i1 > -1 and i2 > 0):
			if run not in runs:
				runs.append(run)
	list.sort(runs)
	return runs

def get_task_runs(funcdir):
	task_runs={}
	if os.path.exists(funcdir):
		files=os.listdir(funcdir)
		for f in files:
			runs=[]
			# find task name
			i1=f.find('_task-')+len('_task-')
			tmp=f[i1:]
			i2=tmp.find('_run-')
			task=tmp[:i2]
			if (i1 > -1 and i2 > -1):
				if task not in task_runs.keys():
					# find runs for this task
					task_runs[task]=get_runs(funcdir,task)
	return task_runs


def get_study_info(studydir,hasSessions):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=get_all_subs(studydir)
	info={}
	for sub in all_subs:
		subdir=os.path.join(fmriprep,'sub-'+sub)
		files=os.listdir(subdir)
		info['sub-'+sub]={}
		if hasSessions:
			 # info = {'sub-01':{'ses-01':{...}}}
			for f in files: # session folders
				if os.path.isdir(os.path.join(subdir,f)) and f.startswith('ses-'):
					funcdir=os.path.join(subdir,f,'func')
					info['sub-'+sub][f]=get_task_runs(funcdir)
		else:
			 # info = {'sub-01':{'taskname':{...}}}
			funcdir=os.path.join(subdir,'func')
			info['sub-'+sub]=get_task_runs(funcdir)
	return info

"""
print 'TESTING WITHOUT SESSIONS'
x='/Users/alicexue/Documents/ShohamyLab/fsl_testing/Flanker'
print get_study_info(x,False)

print ''
print 'TESTING WITH SESSIONS'
x='/Users/alicexue/Documents/ShohamyLab/fsl_testing/Flanker_w_ses'
print get_study_info(x,True)

print ''
print 'TESTING WITH SESSIONS'
x='/Volumes/shohamy-labshare/ANDM_scan/scan_data'
print get_study_info(x,True)
"""

"""
def get_model_dir(studydir):
	model_dir=os.path.join(studydir,'model')
	if os.path.exists(model_dir):
		return model_dir
	else:
		print "model directory not found in %s"%studydir
		return ''



def get_all_tasks(studydir):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=get_all_subs(studydir)
	tasks=[]
	if len(all_subs)>0:
		exsub='sub-'+all_subs[0]
		sessions=get_all_ses(studydir)
		if len(sessions)==0:
			subfuncdir=os.path.join(fmriprep,exsub,'func')
		else:
			subfuncdir=os.path.join(fmriprep,exsub,'ses-'+sessions[0],'func')
		files=os.listdir(subfuncdir)
		for f in files:
			# find task name
			i1=f.find('_task-')+len('_task-')
			tmp=f[i1:]
			i2=tmp.find('_run-')
			task=tmp[:i2]
			if (i1 > -1 and i2 > -1):
				if task not in tasks:
					tasks.append(task)
		list.sort(tasks)
	return tasks

def get_all_runs(studydir):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=get_all_subs(studydir)
	all_tasks=get_all_tasks(studydir)
	tasks_runs={}
	for task in all_tasks:
		runs=[]
		if len(all_subs)>0:
			exsub='sub-'+all_subs[0]
			sessions=get_all_ses(studydir)
			if len(sessions)==0:
				subfuncdir=os.path.join(fmriprep,exsub,'func')
			else:
				subfuncdir=os.path.join(fmriprep,exsub,'ses-'+sessions[0],'func')
			files=os.listdir(subfuncdir)
			for f in files:
				i1=f.find('_task-'+task+'_run-')+len('_task-'+task+'_run-')
				tmp=f[i1:]
				i2=tmp.find('_')
				run=tmp[:i2]
				if (i1 > -1 and i2 > -1):
					if run not in runs:
						runs.append(run)
			list.sort(runs)
		tasks_runs[task]=runs
	return tasks_runs

def get_all_ses(studydir):
	fmriprep=get_fmriprep_dir(studydir)
	all_subs=get_all_subs(studydir)
	sessions=[]
	if len(all_subs)>0:
		exsub='sub-'+all_subs[0]
		subdir=os.path.join(fmriprep,exsub)
		files=os.listdir(subdir)
		for f in files:
			if f.startswith('ses-'):
				sessions.append(f[len('ses-'):])
		list.sort(sessions)
	return sessions

def get_all_models(studydir):
	modeldir=get_model_dir(studydir)
	level1dir=os.path.join(modeldir,'level1')
	level2dir=os.path.join(modeldir,'level2')
	level3dir=os.path.join(modeldir,'level3')
	leveldir=''
	if os.path.exists(level1dir):
		leveldir=level1dir
	elif os.path.exists(level2dir):
		leveldir=level2dir
	elif os.path.exists(level3dir):
		leveldir=level3dir
	files=os.listdir(leveldir)
	models=[]
	for f in files:
		if f.startswith('model'):
			modelname=f[len('model'):]
			models.append(modelname)
	return models
"""

"""
print 'TESTING WITHOUT SESSIONS'
x='/Users/alicexue/Documents/ShohamyLab/fsl_testing/Flanker'
print "fmriprepdir", get_fmriprep_dir(x)
print "subs", get_all_subs(x)
print "tasks",get_all_tasks(x)
print "runs",get_all_runs(x)
print "sessions",get_all_ses(x)
print "models",get_all_models(x)

print ''
print 'TESTING WITH SESSIONS'

x='/Users/alicexue/Documents/ShohamyLab/fsl_testing/Flanker_w_ses'
print "fmriprepdir", get_fmriprep_dir(x)
print "subs", get_all_subs(x)
print "tasks",get_all_tasks(x)
print "runs",get_all_runs(x)
print "sessions",get_all_ses(x)
print "models",get_all_models(x)
"""
