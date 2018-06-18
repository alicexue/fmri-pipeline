"""
Downloads each subject's fmriprep outputs from flywheel

Iterates through all the sessions and analyses
Checks if the subject's fmriprep and reports folder has already been downloaded
Will not overwrite subjects with existing fmriprep and reports folders (will print a skip message)

If fmriprep was run multiple times, downloads the most recent analysis
Downloads everything into a tmp folder
Each subject's fmriprep folder is moved to the fmriprep directory under the directory basedir/studyid
The html and svg outputs are moved to the reports directory (which is at the same level as the fmriprep directory)
When download is complete, the tmp folder is removed
"""

# Notes:
# So far only tested on Ellen's Curiosity project (where fmriprep has only been run on one subject)
# Still needs to be tested on multiple subject analyses
# Still needs to be tested on habanero

# Created by Alice Xue, 06/2018

import flywheel
import subprocess as sp
from pprint import pprint
import os
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
	studydir=os.path.join(basedir,studyid)
	if not os.path.exists(studydir):
		os.makedirs(studydir)
		os.makedirs(os.path.join(studydir,'tmp'))
	tmpdir=os.path.join(studydir,'tmp')
	fmriprepdir=os.path.join(studydir,'fmriprep')
	if not os.path.exists(fmriprepdir):
		os.mkdir(fmriprepdir)
	reportsdir=os.path.join(studydir,'reports')
	if not os.path.exists(reportsdir):
		os.mkdir(reportsdir)

	# Create client
	fw = flywheel.Flywheel(key) # API key

	print '\n## Downloading fmriprep outputs now ##\n'

	group_id=group_id 
	for project in fw.get_group_projects(group_id):
		if project.label==project_label:
			print('Project: %s: %s' % (project.id, project.label))
			for session in fw.get_project_sessions(project.id):
				dates=[]
				analysis_ids={} # key is date, value is analysis.id
				for analysis in fw.get_session_analyses(session.id):
					if 'fmriprep' in analysis.label:
						print('\tAnalysis: %s: %s' % (analysis.id, analysis.label))
						date_created=analysis.created
						analysis_ids[date_created]=analysis.id
						if analysis.files!=None:
							dates.append(date_created)
						
				if len(dates)!=0:
					list.sort(dates)
					most_recent_analysis_id=analysis_ids[dates[-1]]
					"""
					# Doesn't work
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
								sub=name[i1:i2]

								if 'html' in file.name:
									subreportsdir=os.path.join(reportsdir,sub)
									if os.path.exists(subreportsdir):
										print 'Skipping downloading and processing of fmriprep reports for %s'%sub
									else:
										outfile=sub+'.html.zip'
										print 'Downloading', file.name
										filepath=os.path.join(tmpdir,outfile)
										fw.download_output_from_session_analysis(session.id, most_recent_analysis_id, file.name, filepath)
										unzippedfilepath=filepath[:-4]
										print 'Unzipping', filepath, 'to', unzippedfilepath
										sp.call(['unzip',filepath,'-d',unzippedfilepath])
										# Move sub folder in sub-<id>.html->flywheel->...->sub-<id> to the reportsdir
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
										indexhtmlpath=os.path.join(unzippedfilepath,'index.html')
										if os.path.exists(indexhtmlpath):
											subreportsdir=os.path.join(reportsdir,sub)
											print 'Moving %s to %s'%(indexhtmlpath,subreportsdir)
											sp.call(['mv',indexhtmlpath,subreportsdir])
											oldindexhtml=os.path.join(subreportsdir,'index.html')
											newindexhtml=os.path.join(subreportsdir,'%s.html'%sub)
											print 'Renaming %s to %s'%(oldindexhtml,newindexhtml)
											sp.call(['mv',oldindexhtml,newindexhtml])
										sp.call(['rm','-rf',filepath])
										sp.call(['rm','-rf',unzippedfilepath])
									
								elif 'fmriprep' in file.name:
									subfmriprepdir=os.path.join(fmriprepdir,sub)
									if os.path.exists(subfmriprepdir):
										print 'Skipping downloading and processing of fmriprep outputs for %s'%sub
									else:
										outfile=sub+'.zip'
										print 'Downloading', file.name
										filepath=os.path.join(tmpdir,outfile)
										fw.download_output_from_session_analysis(session.id, most_recent_analysis_id, file.name, filepath)
										unzippedfilepath=filepath[:-4]
										print 'Unzipping', filepath, 'to', unzippedfilepath
										sp.call(['unzip',filepath,'-d',unzippedfilepath])
										# Move fmriprep folder to fmriprep
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
										fmriprepsubfigures=os.path.join(newsubfmriprep,'figures')
										if os.path.exists(fmriprepsubfigures):
											print "Removing %s"%fmriprepsubfigures
											sp.call(['rm','-rf',fmriprepsubfigures])
										sp.call(['rm','-rf',filepath])
										sp.call(['rm','-rf',unzippedfilepath])	
	if os.path.exists(tmpdir):
		print 'Removing %s'%tmpdir
		sp.call(['rm','-rf',tmpdir])
				
if __name__ == '__main__':
    main()

