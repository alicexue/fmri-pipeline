# fmri-pipeline

Overview:
- Makes .fsf files for level 1 and level 2 analysis
- Runs fsl's feat on .fsf files in a slurm job array (run_level1.py and run_level2.py)
- These scripts can be run on habanero (which can create job arrays). If these scripts aren't run on a cluster, multiple jobs are run sequentially instead.

Overview:
- Creates *.fsf files for level 1, level 2, and level 3 analysis of fmri data.
- Runs fsl's feat on the created *.fsf files in a slurm job array (or runs feat serially if not running on a cluster).

Requirements:
- fmriprep directory named 'fmriprep'
- func directory (with preprocessed functional files) should be under the subject folder (if there are no sessions) or under the session folder
- anat directory (with preprocessed anatomical files) should be directory under the subject folders (not at the same level as the func directory) (which is how the output of fmriprep should be organized)
- EV files (see step 1 below)
- TR should be specified in a JSON file called task-\<taskname>_bold.json under a directory named 'raw' at the same level as the fmriprep directory (the 'raw' directory should store the raw data files)
- task contrasts (not required) may be specified under the model00\<N> directory as task_contrasts.json or task_contrasts.txt
- requires condition key under model00\<N>

Steps:
1. Run setup.py to create the model directory and all necessary sub-directories. This will also create empty/sample *.json files (model_params.json, condition_key.json, task_contrasts.json) and EVs files for you to fill in. 
-- EV files should be under 
	-> model
		-> level1
			-> model001
				-> sub-\<subid>
					-> task-\<taskname>_run-\<runname>
						-> onsets
	- file should be named: sub-\<subid>_task-\<taskname>_run-\<runname>_ev-00\<N> (can be .txt or .tsv file)
	- note: 
2. Fill out model_params.json under model00\<N>, see Terminology below for explanation of the abbreviations.
3. Fill out condition_key.json under model00\<N>, where the task name is the key and the value is a json object with EV names as the keys and the conditions as the values. (Note: The EV files, *_ev-00\<N>, are always padded with leading zeros so that there are 3 digits)
4. If you need to specify task contrasts, fill out task_contrasts.json, where the key is the task name and the value is a json object in which the key is the name of the contrast and the value is a list that represents the contrast vector. If you don't want to specify task contrasts for this model, remove the file.
5. To run level 1, use run_level1.py, which will create a job array where each job creates a *.fsf file for one run and runs feat on that run. (By default, if the argument specificruns is not specified, all runs are run)
6. Level 2 and level 3 are run similarly - use the -h option to see explanations of the parameters

Terminology and abbreviations:
- studyid: name of the parent directory of the fmriprep directory
- basedir: full path of the grandparent directory of the fmriprep directory
- sub: subject identifier (not including the prefix 'sub-')
- taskname: name of task
- runname: name of run
- smoothing: mm FWHM; default is 0
- use_inplane: use inplane image; default is 0
- nohpf: turn off high pass filtering 
- nowhite: turn off prewhitening
- noconfound: omit motion/confound modeling
- modelnum: model num; default is 1
- anatimg: anatomy image (should be _brain)
- doreg: do registration
- spacetag: space tag for prepreprocessed data (if the functional or anatomical data was preprocessed in multiple spaces, you can specify the space here) (the script will tell you if multiple preprocessed files were found and you need to specify this tag)
- altBETmask: use brainmask from fmriprep (*_brainmask.nii.gz)
- callfeat: automatically calls feat on the *.fsf file that is created by the script
- specificruns: 

Note on file types:
- The EV files can be *.tsv or *.txt files. Just make sure the file is named according to the specification above.

Some behaviors to note:
- For level 1, run_level1.py will exit if no runs have been specified and some feat directories already exist. This prevents the creation of multiple feat directories for the same run (with + appended to the directory name). Upon exit, the program will provide the arguments necessary to create the feat directories for the runs without feats (or you may choose to remove the existing feat directories and create feats for all the runs). The program does not check for existing feat directories if the argument "specificruns" is passed to run_level1.py or mk_all_level1_fsf_bbr.py (This is intentional in order to make sure run_level1 can use mk_all_level1_fsf_bbr seamlessly. However, a warning is printed if the program is creating a feat that already exists). 

Notes:
- The slurm output is out of order (I think because I call feat in a subprocess) but I think the log should still be clear.

To do:
- Check that program doesn't break a task is missing in task_conditions.json
- Integrate with flywheel
