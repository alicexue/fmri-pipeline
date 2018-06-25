#!/usr/bin/env python
"""
Downloads each subject's fmriprep outputs from flywheel

Iterates through all the sessions and analyses
Checks if the subject's fmriprep and reports folder have already been downloaded
Will not overwrite subjects with existing fmriprep and reports folders (will print a skip message)

If fmriprep was run multiple times, downloads the most recent analysis
Downloads everything into a tmp folder
Each subject's fmriprep folder is moved to the fmriprep directory under the directory basedir+studyid
The html and svg outputs are moved to the reports directory (which is at the same level as the fmriprep directory)
When download is complete, the tmp folder is removed
"""

# Created by Alice Xue, 06/2018

import flywheel
import os
from pprint import pprint
import subprocess as sp
import sys

def main():
	if len(sys.argv)!=6:
		print "usage: download_flywheel_fmriprep <Flywheel API key> <Flywheel group_id> <Flywheel project_label> <studyid> <basedir>"
		sys.exit(-1)
	key=sys.argv[1]
	group_id=sys.argv[2]
	project_label=sys.argv[3]
	studyid=sys.argv[4]
	basedir=sys.argv[5]
	download_flywheel_fmriprep(key,group_id,project_label,studyid,basedir)

def download_flywheel_fmriprep(key,group_id,project_label,studyid,basedir):
	# Creates tmp, fmriprep, and reports directories if they don't exist
	studydir=os.path.join(basedir,studyid)
	if not os.path.exists(studydir):
		os.mkdir(studydir)
	tmpdir=os.path.join(studydir,'tmp')
	if not os.path.exists(tmpdir):
		os.mkdir(os.path.join(tmpdir))
	fmriprepdir=os.path.join(studydir,'fmriprep')
	if not os.path.exists(fmriprepdir):
		os.mkdir(fmriprepdir)
	reportsdir=os.path.join(studydir,'reports')
	if not os.path.exists(reportsdir):
		os.mkdir(reportsdir)

	# Create client
	fw = flywheel.Flywheel(key) # API key

	print '\n## Downloading fmriprep outputs now ##\n'

	# Iterates through given project
	for project in fw.get_group_projects(group_id):
		if project.label==project_label:
			print('Project: %s: %s' % (project.id, project.label))
			for session in fw.get_project_sessions(project.id):
				dates=[]
				analysis_ids={} # key is date, value is analysis.id
				for analysis in fw.get_session_analyses(session.id):
					# looks for fmriprep analyses
					if 'fmriprep' in analysis.label:
						print('\tAnalysis: %s: %s' % (analysis.id, analysis.label))
						date_created=analysis.created
						analysis_ids[date_created]=analysis.id
						if analysis.files!=None: # checks for output files - that fmriprep succeeded 
							dates.append(date_created)
						
				if len(dates)!=0:
					list.sort(dates)
					most_recent_analysis_id=analysis_ids[dates[-1]] # if fmriprep was run multiple times, uses most recent analysis
					"""
					# Doesn't work at the moment
					try:
						print "Downloading session analysis"
						fw.download_session_analysis_outputs(session.id, analysis.id)
					except flywheel.ApiException as e:
						print 'Could not use fw.download_session_analysis_outputs'
						print('API Error: %d -- %s' % (e.status, e.reason))
					"""
					for file in analysis.files:
						print file.name
						name = file.name
						if 'sub-' in name:
							i1 = name.find('sub-')
							i2 = name.find('.')
							if i1 > -1 and i2 > -1:
								sub=name[i1:i2] # sub is the subject ID with 'sub-' removed

								# get fmriprep reports (html and svg files)
								if 'html' in file.name: # sub-<id>.html.zip
									subreportsdir=os.path.join(reportsdir,sub)
									if os.path.exists(subreportsdir):
										print 'Skipping downloading and processing of fmriprep reports for %s'%sub
									else:
										# download the file
										outfile=sub+'.html.zip'
										print 'Downloading', file.name
										filepath=os.path.join(tmpdir,outfile)
										fw.download_output_from_session_analysis(session.id, most_recent_analysis_id, file.name, filepath)
										unzippedfilepath=filepath[:-4]
										# unzip the file
										print 'Unzipping', filepath, 'to', unzippedfilepath
										sp.call(['unzip',filepath,'-d',unzippedfilepath])
										# Move sub folder in sub-<id>.html->flywheel->...->sub-<id> to the reportsdir
										# iterates through the flywheel folder to find sub folder buried inside
										# the variable i is used to avoid an infinite loop
										i=10
										curdir=''
										fullcurdir=os.path.join(unzippedfilepath,'flywheel')
										moved=False
										while i > 0 and curdir!=sub:
											if sub in os.listdir(fullcurdir):
												subreportdir=os.path.join(fullcurdir,sub)
												if os.path.exists(subreportdir):
													print "Moving %s to %s"%(subreportdir,reportsdir)
													sp.call(['mv',subreportdir,reportsdir])
												moved=True
											if len(os.listdir(fullcurdir))>0:
												# assuming only one directory in fullcurdir
												for folder in os.listdir(fullcurdir):
													if os.path.isdir(os.path.join(fullcurdir,folder)):
														curdir=folder
														fullcurdir=os.path.join(fullcurdir,folder)
											i-=1;
										if not moved:
											print "Could not find %s in %s.html"%(sub,sub)
										# moves and renames index.html to sub-<id>.html
										indexhtmlpath=os.path.join(unzippedfilepath,'index.html')
										if os.path.exists(indexhtmlpath):
											subreportsdir=os.path.join(reportsdir,sub)
											print 'Moving %s to %s'%(indexhtmlpath,subreportsdir)
											sp.call(['mv',indexhtmlpath,subreportsdir])
											oldindexhtml=os.path.join(subreportsdir,'index.html')
											newindexhtml=os.path.join(subreportsdir,'%s.html'%sub)
											print 'Renaming %s to %s'%(oldindexhtml,newindexhtml)
											sp.call(['mv',oldindexhtml,newindexhtml])
										# remove originally downloaded files
										sp.call(['rm','-rf',filepath])
										sp.call(['rm','-rf',unzippedfilepath])
								
								# get fmriprep outputs
								elif 'fmriprep' in file.name: # fmriprep_output_sub-<id>.zip
									subfmriprepdir=os.path.join(fmriprepdir,sub)
									if os.path.exists(subfmriprepdir):
										print 'Skipping downloading and processing of fmriprep outputs for %s'%sub
									else:
										outfile=sub+'.zip'
										# downloads outputs
										print 'Downloading', file.name
										filepath=os.path.join(tmpdir,outfile)
										fw.download_output_from_session_analysis(session.id, most_recent_analysis_id, file.name, filepath)
										# unzips outputs
										unzippedfilepath=filepath[:-4] # removes .zip from name 
										print 'Unzipping', filepath, 'to', unzippedfilepath
										sp.call(['unzip',filepath,'-d',unzippedfilepath])
										# Move downloaded fmriprep folder to fmriprep
										unzippedfmriprep=os.path.join(unzippedfilepath,'fmriprep',sub)
										newsubfmriprep=os.path.join(fmriprepdir,'%s'%sub)
										if os.path.exists(unzippedfilepath):
											try:
												print "Moving %s to %s"%(unzippedfmriprep,fmriprepdir)
												sp.call(['mv',unzippedfmriprep,fmriprepdir])
											except:
												print "Could not move %s to %s"%s(unzippedfmriprep,newsubfmriprep)
										else:
											print "Could not find %s"%unzippedfmriprep
										# Remove figures directory from sub folder in fmriprep 
										# the figures direcotry is a duplicate of the fmriprep reports, which are downloaded separately into the reports directory
										fmriprepsubfigures=os.path.join(newsubfmriprep,'figures')
										if os.path.exists(fmriprepsubfigures):
											print "Removing %s"%fmriprepsubfigures
											sp.call(['rm','-rf',fmriprepsubfigures])
										sp.call(['rm','-rf',filepath])
										sp.call(['rm','-rf',unzippedfilepath])	
	# remove the tmp directory
	if os.path.exists(tmpdir):
		print 'Removing %s'%tmpdir
		sp.call(['rm','-rf',tmpdir])
				
if __name__ == '__main__':
    main()

