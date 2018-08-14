#!/usr/bin/env python
"""
Downloads each subject's fmriprep outputs from flywheel
Iterates through all the sessions and analyses
Checks if the subject's fmriprep and reports folder for the given session have already been downloaded
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
	freesurferdir=os.path.join(studydir,'freesurfer')
	if not os.path.exists(freesurferdir):
		os.mkdir(freesurferdir)
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
						# assumes subject ID is between sub- and _ or between sub- and .
						if 'sub-' in name:
							i1 = name.find('sub-')
							tmpname=name[i1:]
							if '_' in tmpname:
								i2 = tmpname.find('_')
							else:
								i2 = tmpname.find('.')
							if i1 > -1 and i2 > -1:
								sub=tmpname[:i2] # sub is the subject ID with 'sub-' removed
								print "Subject ID:", sub

								# get fmriprep reports (html and svg files)
								if 'html' in file.name: # sub-<id>.html.zip
									subreportsdir=os.path.join(reportsdir,sub)
									subsesreportsdir=os.path.join(reportsdir,sub,'ses-'+session['label'])
									if os.path.exists(subsesreportsdir):
										print 'Skipping downloading and processing of fmriprep reports for %s/ses-%s'%(sub,session['label'])
									else:
										downloadSessionOnly=False
										if os.path.exists(subreportsdir):
											downloadSessionOnly=True
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
												desireddir=os.path.join(fullcurdir,sub)
												targetdir=reportsdir
												if downloadSessionOnly:
													desireddir=os.path.join(fullcurdir,sub,'ses-'+session['label'])
													targetdir=os.path.join(reportsdir,sub)
												#if not os.path.exists(targetdir):
												#	os.mkdir(targetdir)
												if os.path.exists(desireddir):
													print "Moving %s to %s"%(desireddir,targetdir)
													sp.call(['mv',desireddir,targetdir])
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
											newindexhtml=os.path.join(subreportsdir,'ses-'+session['label'],'%s.html'%sub)
											print 'Renaming %s to %s'%(oldindexhtml,newindexhtml)
											sp.call(['mv',oldindexhtml,newindexhtml])
										# remove originally downloaded files
										sp.call(['rm','-rf',filepath])
										sp.call(['rm','-rf',unzippedfilepath])
								
								# get fmriprep outputs
								elif file.name.startswith('fmriprep_'+sub): # fmriprep_sub-<subid>_<random alphanumericcode?>.zip
									subfmriprepdir=os.path.join(fmriprepdir,sub)
									subsesfmriprepdir=os.path.join(fmriprepdir,sub,'ses-'+session['label'])
									if os.path.exists(subsesfmriprepdir):
										print 'Skipping downloading and processing of fmriprep outputs for %s'%sub
									else:
										downloadSessionOnly=False
										if os.path.exists(subfmriprepdir):
											downloadSessionOnly=True
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

										# iterates through the unzipped sub folder to find fmriprep folder buried inside
										# the variable i is used to avoid an infinite loop
										i=3
										curdir=''
										fullcurdir=unzippedfilepath
										moved=False
										while i > 0 and curdir!='fmriprep':
											if 'fmriprep' in os.listdir(fullcurdir):
												desireddir=os.path.join(fullcurdir,'fmriprep',sub)
												targetdir=fmriprepdir
												if downloadSessionOnly:
													desireddir=os.path.join(fullcurdir,'fmriprep',sub,'ses-'+session['label'])
													targetdir=os.path.join(fmriprepdir,sub)

												tmpsubfmriprepdir=os.path.join(fullcurdir,'fmriprep',sub)
												if os.path.exists(desireddir):
													print "Moving %s to %s"%(desireddir,targetdir)
													sp.call(['mv',desireddir,targetdir])
													moved=True
											if 'freesurfer' in os.listdir(fullcurdir):
												tmpsubfreesurferdir=os.path.join(fullcurdir,'freesurfer',sub)
												if os.path.exists(tmpsubfreesurferdir) and not os.path.exists(os.path.join(freesurferdir,sub)):
													print "Moving %s to %s"%(tmpsubfreesurferdir,freesurferdir)
													sp.call(['mv',tmpsubfreesurferdir,freesurferdir])
													moved=True
											if len(os.listdir(fullcurdir))>0:
												# assuming only one directory in fullcurdir
												for folder in os.listdir(fullcurdir):
													if os.path.isdir(os.path.join(fullcurdir,folder)):
														curdir=folder
														fullcurdir=os.path.join(fullcurdir,folder)
											i-=1;
										if not moved:
											print "Could not find fmriprep in %s"%sub

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
