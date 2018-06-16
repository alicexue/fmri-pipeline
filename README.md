# fmri-pipeline

## Overview:
- manage_flywheel_downloads.py downloads fmriprep outputs and raw BIDS from Flywheel

- Creates *.fsf files for level 1, level 2, and level 3 analysis of fmri data.
- Runs fsl's feat on the created *.fsf files in a slurm job array (or runs feat serially if not running on a cluster).

## Requirements:

#### For downloading data from Flywheel:
- [Flywheel CLI](https://docs.flywheel.io/display/EM/CLI+-+Installation) must be installed (and have your API key handy)
- to export raw BIDS, you must have [Docker](https://docs.docker.com/install/#cloud) installed and running


#### For running fmri analyses:
- directory with fmriprep output named 'fmriprep'
- func directories (with preprocessed functional files) should be under the subject folder (if there are no sessions) or under the appropriate session folder
- anat directories (with preprocessed anatomical files) should be under each subject folder (not at the same level as the func directory if there are sessions) (which is how the output of fmriprep should be organized) (see File Structure below)
- EV files (see step 1 below)
- TR should be specified in a JSON file called task-\<taskname>_bold.json under a directory named 'raw' at the same level as the fmriprep directory (the 'raw' directory should store the raw data files). "RepetitionTime" should be the key.
- model params must be specified under the model00\<N> directory (see step 2 below)
- condition key must be specified under the model00\<N> directory as condition_key.json or condition_key.txt (see step 3 below)
- task contrasts (not required) may be specified under the model00\<N> directory as task_contrasts.json or task_contrasts.txt (see step 4 below)

## Steps:

#### For downloading data from Flywheel:
1. Run manage_flywheel_downloads.py, which will ask for the necessary information via the command line

#### For running fmri analyses:
1. Run setup.py to create the model directory and all necessary sub-directories. This will also create empty/sample *.json files (model_params.json, condition_key.json, task_contrasts.json) and EVs files for you to fill in. 
2. Fill out model_params.json under model00\<N>, see Terminology below for explanation of the abbreviations.
3. Fill out condition_key.json under model00\<N>, where the task name is the key and the value is a json object with EV names as keys and the conditions as values. (Note: The EV files, *_ev-00\<N>, are always padded with leading zeros so that there are 3 digits)
4. If you need to specify task contrasts, fill out task_contrasts.json, where the key is the task name and the value is a json object in which the key is the name of the contrast and the value is a list that represents the contrast vector. If you don't want to specify task contrasts for this model, remove the file.
5. Create the EV files. setup.py creates one sample EV file - with the correct file name - in a folder called 'onsets' under each run folder. Make sure to follow the same naming system when creating more EV files.
6. To run level 1, use run_level1.py, which will create a job array where each job creates a *.fsf file for one run and runs feat on that run. (By default, if the argument specificruns is not specified, fsf's will be created for all runs)
7. Level 2 and level 3 are run similarly. Use the -h option to see explanations of the parameters

## File Structure:
```
basedir
│
└───<studyid>
    │
    └───raw
    │   |   task-<task>_bold.json
    │
    │
    └───fmriprep
    │	│
    │	└───anat (has preprocessed data)
    │	│
    │	└───ses-01
    │	    │
    │	    └───anat
    │	    │
    │	    └───func (has preprocessed data)
    │
    └───model
        │
        └───level<N>
	    │
	    └───model00<N>
	    	│   model_params.json
		│   condition_key.json
		│   task_contrasts.json
	    	│
		└───sub-<subid>
		    │
		    └───task-<taskname>_run-<runname>
		        │
			└───onsets
			    │   sub-<subid>_task-<taskname>_run-<runname>_ev-00<N> (can be .txt or .tsv file) 
			    │
```

## Terminology and abbreviations:
- **studyid**: name of the parent directory of the fmriprep directory
- **basedir**: full path of the grandparent directory of the fmriprep directory (don't include studyid here)
- **sub**: subject identifier (not including the prefix 'sub-')
- **taskname**: name of task
- **runname**: name of run
- **smoothing**: mm FWHM; default is 0
- **use_inplane**: use inplane image; default is 0
- **nohpf**: turn off high pass filtering 
- **nowhite**: turn off prewhitening
- **noconfound**: omit motion/confound modeling
- **modelnum**: model num; default is 1
- **anatimg**: anatomy image (should be _brain)
- **doreg**: do registration
- **spacetag**: space tag for prepreprocessed data (if the functional or anatomical data was preprocessed in multiple spaces, you can specify the space here) (the script will tell you if multiple preprocessed files were found and you need to specify this tag)
- **altBETmask**: use brainmask from fmriprep (*_brainmask.nii.gz)
- **callfeat**: automatically calls feat on the *.fsf file that is created by the script
- **specificruns**: JSON object in a string that details which runs to create fsf's for. If specified, ignores specificruns specified in model_params.json. Ex: If there are sessions: '{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}' where flanker is a task name and ["1", "2"] is a list of the runs. If there aren't sessions: '{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}'. Make sure this describes the fmriprep folder, which should be in BIDS format. Make sure to have single quotes around the JSON object and double quotes within.

## Note on file types:
- The EV files can be *.tsv or *.txt files. Just make sure the file is named according to the specification above.
- condition_key and task_contrasts can be *.json or *.txt 

## Some behaviors to note:
- For level 1, run_level1.py will exit if no runs have been specified and some feat directories already exist. This prevents the creation of multiple feat directories for the same run (with + appended to the directory name). Upon exit, the program will print the additional arguments necessary to create the feat directories for the runs missing feats (or you may choose to remove the existing feat directories and create feats for all the runs). The program does not check for existing feat directories if the argument "specificruns" is passed to run_level1.py or mk_all_level1_fsf_bbr.py (This is intentional in order to make sure run_level1 can use mk_all_level1_fsf_bbr seamlessly. However, a warning is printed if the program is creating a feat that already exists). (The same thing happens if all feat directories for all tasks exist.) 

## Notes:
- The slurm output is out of order (I think because some things are run in a subprocess). The log should still be clear.
- Flywheel downloads haven't been tested on habanero yet. Also need to test downloading fmriprep output for multiple subjects.

## To do:
- Check for preprocessed anat files in the anat folder under subject folder AND under session folder
- TR: currently checks in raw->task-\<task>_bold.json. Need to also check under raw->sub->func->sub\<sub>_task-\<task>_run-\<run>_bold.json. May also want to require specifying TR under model.
- Accomodate not having multiple runs (not having run in the file names)...
- Integrate with flywheel
