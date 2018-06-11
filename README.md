# fmri-pipeline

06/08/2018
Overview:
- Makes .fsf files for level 1 and level 2 analysis
- Runs fsl's feat on .fsf files in a slurm job array (run_level1.py and run_level2.py)

Details:
Creates model directory on the same level as fmriprep directory
(name of parent directory of fmriprep directory should be specified as the argument "studyid")
(name of grandparent directory of fmriprep directory should be specified as the argument "basedir")
 
Works with fmriprep directory where
- preprocessed anat directory is directly under subject folder
- preprocessed func directory is directly under subject folder (if there are no sessions) or under session folder 
- requires EV files to already be created in the following directory:
	-> model
		-> level1
			-> model001
				-> sub-<subid>
					-> task-<taskname>_run-<runname>
						-> onsets
	- file should be named: sub-<subid>_task-<taskname>_run-<runname>_ev-00<N> (can be .txt or .tsv file)
	- note: ev number is always padded with leading zeros so that there are 3 digits	
- requires TR to be specified in a JSON file called task-<taskname>_bold.json under a directory named "raw" at the same level as the fmriprep directory 
- task contrasts may be specified under the model00<N> directory as task_contrasts.json or task_contrasts.txt
- requires condition key under model00<N>
- Note on JSON and txt files:
	- compatible with both
