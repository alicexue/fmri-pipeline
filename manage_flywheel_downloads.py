"""
Takes command line input and runs download_flywheel_fmriprep and export_raw_bids accordingly
"""

# Created by Alice Xue, 06/2018

import subprocess as sp
import sys
import os
import flywheel
import download_flywheel_fmriprep
import export_raw_bids


dockerExists=False
try:
	FNULL = open(os.devnull, 'w')
	sp.call(['docker'],stdout=FNULL, stderr=sp.STDOUT)
	dockerExists=True
except:
	dockerExists=False

loggedIn=False
while not loggedIn:
	key=raw_input('Enter Your Flywheel API Key: ')
	try:
		fw = flywheel.Flywheel(key) 
		loggedIn=True
	except:
		print 'Invalid API key.'

self = fw.get_current_user()
print 'You can ignore the UserWarning.'
print('\nYou are now logged in as %s %s.' % (self.firstname, self.lastname))

groups=fw.get_all_groups()

print ''
if len(groups)>0:
	print 'Here are your groups:'
	for group in fw.get_all_groups():
		print('%s: %s' % (group.id, group.label))
group_id=raw_input('Enter the group id: ')

print ''
projects=fw.get_group_projects(group_id)
if len(projects)>0:
	print 'Here are your projects:'
	project_labels=[]
	for project in projects:
		project_id=project.id
		project_labels.append(project.label)
		print('Project label: %s' % (project.label))
	my_project=''
	my_project=raw_input('Enter the project label: ')
	while my_project not in project_labels:
		print "HERE",my_project,project_labels
		print '\nInvalid project label. See list of project labels above'
		my_project=raw_input('Enter the project label: ')
	project_label=my_project
else:
	while len(fw.get_group_projects(group_id))==0:
		print 'No projects found in group %s.'%(group_id)
		print 'Are you sure the group id is %s?'%(group_id)
		group_id=raw_input('Enter the group id: ')
	print '\nHere are your projects:'
	projects=fw.get_group_projects(group_id)
	project_labels=[]
	for project in projects:
		project_id=project.id
		project_labels.append(project.label)
		print('Project label: %s' % (project.label))
	my_project=''
	my_project=raw_input('Enter the project label: ')
	while my_project not in project_labels:
		print "HERE",my_project, project_labels
		print '\nInvalid project label. See list of project labels above'
		my_project=raw_input('Enter the project label: ')
	project_label=my_project
	

print '\nThe study id is the name of the directory that the fmriprep output will be downloaded to.'
studyid=raw_input('Enter the study id: ')
print '\nThe base directory is the full path of where the study id directory will be created. (Don\'t include study id here.)'
basedir=raw_input('Enter the base directory: ')
while not os.path.exists(basedir):
	print 'Invalid base directory.'
	basedir=raw_input('Enter the base directory: ')

studydir=os.path.join(basedir,studyid)
if not os.path.exists(studydir):
	print '\nNote: %s does not exist. It will be created.'%studydir
else:
	print '\nNote: %s already exists. Only the remaining subjects\' data will be downloaded.'%studydir

exportRawBids=False
if dockerExists:
	rsp=''
	print ''
	while rsp!='y' and rsp!='n':
		rsp=raw_input('Do you want to download the raw BIDS data for your subjects? (y/n) ')
		if rsp=='y':
			exportRawBids=True
			rsp2=''
			while rsp2!='y' and rsp2!='n':
				rsp2=raw_input('Docker is needed to export the raw BIDS data. Is docker running? (y/n) ')
			if rsp2=='n':
				print 'Since docker is not running, raw BIDS won\'t be exported.'
				exportRawBids=False
else:
	print 'Note: docker is not installed. Raw BIDS cannot be exported.'

download_flywheel_fmriprep.download_flywheel_fmriprep(key,group_id,project_label,studyid,basedir)
if exportRawBids:
	export_raw_bids.export_raw_bids(studyid,basedir,project_label)
