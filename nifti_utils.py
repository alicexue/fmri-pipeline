#!/usr/bin/env python
"""
Processes header of Nifti files
"""

# Created by Alice Xue, 06/2018

import subprocess


def read_nifti_header(niftifile):
    """
    Args:
        niftifile (str): full path of niftifile
    Returns:
        dictionary with original variables in header as keys and the values as their respective values
    """
    p = subprocess.Popen(['fslinfo', niftifile], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf8')
    output, errors = p.communicate()
    l1 = output.split('\n')
    header_vals = {}
    for line in l1:
        tmp = line.replace('\t', ' ').split(' ')
        if tmp[0] != '':
            header_vals[tmp[0]] = tmp[-1]
    return header_vals


def get_tr(niftifile):
    """
    Args:
        niftifile (str): full path of niftifile
    Returns:
        the Repetition Time as a floating number
    """
    header_vals = read_nifti_header(niftifile)
    tr = float(header_vals['pixdim4'])
    if tr >= 1000:
        tr = tr / 1000 
        print("NOTE: TR information in file header appears to be in milliseconds rather than seconds; converting to seconds for compatibility with FSL: %ss" % tr)
    return tr
