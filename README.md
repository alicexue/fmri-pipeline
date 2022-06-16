# fmri-pipeline

## Overview:
- Data stored on Flywheel, including raw BIDS data, fmriprep outputs, freesurfer outputs, and html/svg reports can be downloaded using manage_flywheel_downloads.py. Fmriprep outputs is saved in BIDS format.

- Creates *.fsf files (see [FSL FEAT](https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FEAT)) for level 1, level 2, and level 3 analysis of fMRI data
- Runs fsl's feat on the generated *.fsf files in parallel on a slurm job array (or runs feat serially if not running on a cluster)

## Requirements:

#### For downloading data from Flywheel:
- Install the [Flywheel Python SDK](https://flywheel-io.gitlab.io/product/backend/sdk/branches/master/python/getting_started.html) to download fmriprep outputs from Flywheel. 
- Have your Flywheel API key handy (see your user profile). 
- To export raw BIDS, you must have [Docker](https://docs.docker.com/get-docker/) installed and running and the [Flywheel CLI](https://docs.flywheel.io/hc/en-us/articles/360008162214-Installing-the-Flywheel-Command-Line-Interface-CLI-) installed. Make sure to log into the CLI with your API key.
- Required packages are listed in requirements.txt. To install all packages in requirements.txt at once, use the command "pip install -r requirements.txt"

#### For running fmri analyses:
- directory with fmriprep output named 'fmriprep'
- func directories (with preprocessed functional files) should be in the subject folder (if there are no sessions) or in the appropriate session folder
- anat directories (with preprocessed anatomical files) can be in the subject folder or in the appropriate session folder
- EV files (see step 1 below)
- model params must be specified under the model-\<modelname> directory (see step 2 below)
- condition key must be specified under the model-\<modelname> directory as condition_key.json or condition_key.txt (see step 3 below)
- task contrasts (not required) may be specified under the model-<modelname> directory as task_contrasts.json or task_contrasts.txt (see step 4 below)

## Steps:

#### For downloading data from Flywheel:
1. Run manage_flywheel_downloads.py, which will ask for the necessary information via the command line
2. Run rm_fmriprep_ses_directories.py if Flywheel adds unwanted session directories to fmriprep outputs

#### For running fmri analyses:
1. Run setup.py to create the model directory and all necessary sub-directories. This will also create empty/sample *.json files (model_params.json, condition_key.json, task_contrasts.json) and onset directories for the EV files. 
2. Fill out model_params.json under model-\<modelname>, see abbreviation explanations below.
3. Fill out condition_key.json under model-\<modelname>, where the task name is the key and the value is a json object with EV names as keys and the conditions as values. (Note: The EV files, *_ev-00\<N>, are always padded with leading zeros so that there are 3 digits)
4. If you need to specify task contrasts, fill out task_contrasts.json, where the key is the task name and the value is a json object in which the key is the name of the contrast and the value is a list that represents the contrast vector. If you don't want to specify task contrasts for this model, remove the file.
5. Create the EV files, which belong in the 'onsets' directories under each run folder. Make sure the EV files are named correctly (see the diagram below). Confound files should be saved in the same location as the EV files (the file name ends in *_ev-confounds, see below).
6. If customization of fsf files is desired, create a custom stub file named design_level\<N>_custom.stub under the model directory with feat settings (see design_level1_fsl5.stub for examples). If a setting in the custom file is found in the stub file, the custom setting will replace the existing setting. If the custom setting is not found, it will be added to the fsf.
7. To run level 1, use run_level1.py, which will create a job array where each job creates a *.fsf file for one run and runs feat on that run. (By default, if the argument specificruns is not specified, fsf's will be created for all runs)
8. Level 2 and level 3 are run similarly. Use the -h option to see explanations of the parameters

## Directory Structure:
- Session directories are optional. If there aren't multiple sessions, omit the session label from EV file names.
```
basedir
│
└───<studyid>
    │
    └───raw
    │
    └───freesurfer
    │
    └───fmriprep
    │	│
    │	└───anat (can have preprocessed data here or below, under ses-<sesname>)
    │	│
    │	└───ses-<sesname>
    │	    │
    │	    └───anat (can have preprocessed data here)
    │	    │
    │	    └───func (has preprocessed data)
    │
    └───model
        │
        └───level<N>
	    │
	    └───model-<modelname>
	    	│   model_params.json
		│   condition_key.json
		│   task_contrasts.json
		|   design_level<N>_custom.stub (optional)
	    	│
		└───sub-<subid>
		    │
		    │
		    └───ses-<sesname>
			│
		        └───task-<taskname>_run-<runname>
			    │
			    └───onsets
			        │   sub-<subid>_ses-<sesname>_task-<taskname>_run-<runname>_ev-00<N> (can be .txt or .tsv file) 
			        |   sub-<subid>_ses-<sesname>_task-<taskname>_run-<runname>_ev-confounds (can be .txt or .tsv file) 
			        │
	
```

## Explanations of input parameters:
- **studyid**: name of the parent directory of the fmriprep directory
- **basedir**: full path of the grandparent directory of the fmriprep directory (don't include studyid here)
- **sub**: subject identifier (not including the prefix 'sub-')
- **modelname**: name of model (string)
- **taskname**: name of task
- **runname**: name of run
- **smoothing**: mm FWHM; default is 0
- **use_inplane**: use inplane image; default is 0
- **nohpf**: turn off high pass filtering 
- **nowhite**: turn off prewhitening
- **noconfound**: omit motion/confound modeling
- **anatimg**: anatomy image (should be _brain)
- **doreg**: do registration
- **spacetag**: space tag for prepreprocessed data (if the functional or anatomical data was preprocessed in multiple spaces, you can specify the space here) (the script will tell you if multiple preprocessed files were found and you need to specify this tag)
- **altBETmask** (deprecated in favor of usebrainmask): use brainmask from fmriprep (*_brainmask.nii.gz)
- **usebrainmask**: apply brain mask to *_preproc.nii.gz by running fslmaths's -mas on *_brainmask.nii.gz and set output to *_preproc_brain.nii.gz. Instead of setting "feat_files(1)" in .fsf to *_preproc.nii.gz, set the output name to *_preproc_brain_nii.gz. If "nofeat" is True, the .fsf will point to *_preproc_brain_nii.gz for "feat_files(1)" but will not create *_preproc_brain_nii.gz. fslmaths's -mas will only be called when feat is also being run
- **callfeat**: (option for mk_level1_fsf.py and mk_level2_fsf.py) automatically calls feat on the *.fsf file that is created by the script
- **specificruns**: JSON object in a string that details which runs to create fsf's for. If specified, ignores specificruns specified in model_params.json. Ex: If there are sessions: '{"sub-01": {"ses-01": {"flanker": ["1", "2"]}}, "sub-02": {"ses-01": {"flanker": ["1", "2"]}}}' where flanker is a task name and ["1", "2"] is a list of the runs. If there aren't sessions: '{"sub-01":{"flanker":["1"]},"sub-02":{"flanker":["1","2"]}}'. Make sure this describes the fmriprep folder, which should be in BIDS format. Make sure to have single quotes around the JSON object and double quotes within.
- **nofeat**: (option for run_level1.py, run_level2.py, get_level1_jobs.py, get_level2_jobs.py, mk_all_level3_fsf.py) don't run feat on each of the *.fsf files created

## Note on file types:
- The EV files can be *.tsv or *.txt files. Just make sure the file is named according to the specification above.
- condition_key and task_contrasts can be *.json or *.txt 
- In json objects, strings must be in double quotes, not single quotes. You can check the the json files are formatted properly using this [json formatter](https://jsonformatter.org/)

## Some behaviors to note:
- If some feats already exist, warnings will be printed out. Existing feats are never overwritten, but there is an option to remove existing feats. 
- If specificruns isn't specified through the command line, specificruns from modelparams.json is used. If specificruns in modelparams.json is empty, then the script is run on all runs for all tasks for all subjects (based on the data provided in the fmriprep directory).
- Re: downloading and exporting data from flywheel - if the subject folder for fmriprep/reports/freesurfer does not exist, entire analysis output for that subject will be downloaded. If that subject folder does exist, only the session folder will be moved to the subject directory. (For freesurfer however, only one session will be downloaded. There are no session folders under the subject freesurfer directory)

## Notes:
- TR is obtained by reading the header of the Nifti file (preproc func file)
- altBETmask has been deprecated in favor of usebrainmask (see above)
