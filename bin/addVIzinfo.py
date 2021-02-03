import shutil
import unittest
from datetime import datetime
import json
import numpy as np
import fitsio
import glob
import argparse
from astropy.table import Table,join,unique,vstack
from matplotlib import pyplot as plt


#assumes gathSV_zinfo.py has been run for all tracer types for arguments below

parser = argparse.ArgumentParser()
parser.add_argument("--release", help="what spectro release to use, e.g. blanc or daily",default='blanc') #eventually remove this and just gather everything
parser.add_argument("--basedir", help="base directory for output, default is CSCRATCH",default=os.environ['CSCRATCH'])
parser.add_argument("--version", help="catalog version to load from",default='test')
args = parser.parse_args()
print(args)

types = ['ELG','LRG','BGS_ANY']#'QSO',
tiles = ['80608','80609','80613']#'na',]

dirvi = '/global/cfs/cdirs/desi/sv/vi/TruthTables/Blanc/'
dirz = svdir+'redshift_comps/'+release+'/'+version+'/'

for i in range(0,len(types)):
    tp =types[i]
    tile = tiles[i]
    tt=Table.read(dir+tp[:3]+'/'+'desi-vi_'+tp[:3]+'_tile'+tile+'_nightdeep_merged_all_210203.csv',format='pandas.csv')
    tt.keep_columns(['TARGETID','best_z','best_quality','best_spectype','all_VI_issues','all_VI_comments','merger_comment','N_VI'])
    tz = Table.read(dirz+'/'+tp+'/'+tile+'_'+tp+'zinfo.fits')
    tj = join(td,tt,join_type='left',keys='TARGETID')
    tj['N_VI'].fill_value = 0
    tj['N_VI'] = tt['N_VI'].filled() #should easily be able to select rows with N_VI > 0 to get desired info
    tj.write(dirz+'/'+tp+'/'+tile+'_'+tp+'zinfo_wVI.fits',format='fits',overwrite=True)
    print('wrote file with VI info to '+dirz+'/'+tp+'/'+tile+'_'+tp+'zinfo_wVI.fits')
