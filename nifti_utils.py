#!/usr/bin/env python
import subprocess

def read_nifti_header(niftifile):
	p=subprocess.Popen(['fslinfo',niftifile],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	output, errors=p.communicate()
	l1 = output.split('\n')
	header_vals={}
	for line in l1:
		tmp=line.split(' ')
		if tmp[0]!='':
			header_vals[tmp[0]]=tmp[-1]
	return header_vals

def get_TR(niftifile):
	header_vals=read_nifti_header(niftifile)
	return float(header_vals['pixdim4'])