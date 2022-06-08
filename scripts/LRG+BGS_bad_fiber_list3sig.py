import numpy as np
#!pip install astropy
#!pip install fitsio
from scipy import stats
from scipy.stats import norm
import fitsio
import glob
import os
import matplotlib.pyplot as plt
import statistics
import argparse
import astropy
from astropy.table import Table,join
from astropy.time import Time
from astropy.io import fits

parser = argparse.ArgumentParser()
#parser.add_argument("--type", help="tracer type to be selected")
basedir='/global/cfs/cdirs/desi/survey/catalogs'
parser.add_argument("--basedir", help="base directory for output, default is CSCRATCH",default=basedir)
parser.add_argument("--version", help="catalog version; use 'test' unless you know what you are doing!",default='test')
parser.add_argument("--survey", help="e.g., main (for all), DA02, any future DA",default='DA02')
parser.add_argument("--verspec",help="version for redshifts",default='guadalupe')

args = parser.parse_args()
basedir = args.basedir
version = args.version
survey  = args.survey
specver = args.verspec

filepathLF = basedir+'/'+survey+'/LSS/'+specver+'/LSScats/'+version+'/LRG_full.dat.fits'
filepathBGS = basedir+'/'+survey+'/LSS/'+specver+'/LSScats/'+version+'/BGS_ANY_full.dat.fits'



ff = fitsio.read(filepathLF)
hdul = fits.open(filepathLF)
ff2 = fitsio.read(filepathBGS)
hdul = fits.open(filepathBGS)

z_suc= ff['ZWARN']==0
z_suc &= ff['DELTACHI2']>15
z_suc &= ff['Z_not4clus']<1.5
z_tot = ff['ZWARN'] != 999999

#print(len(ff[z_suc]),len(ff[z_tot]))
print("zsuccess rate for LRG=",len(ff[z_suc])/len(ff[z_tot]))
cat1 = Table(ff[z_tot])

full=Table()
full['FIBER'] = np.arange(5000)

fiberstats = Table()
fiberstats['FIBER'], fiberstats['n_tot'] = np.unique(ff['FIBER'][z_tot], return_counts=True)
#fiberstats.sort('n_tot')

tt = Table()
tt['FIBER'], tt['n_suc'] = np.unique(ff['FIBER'][z_suc], return_counts=True)

fiberstats1 = join(fiberstats, tt, keys='FIBER', join_type='outer').filled(0)
fiberstats1 = join(fiberstats1,full, keys='FIBER',join_type='outer').filled(0)
#fiberstats1['frac_suc'] = fiberstats1['n_suc']/fiberstats1['n_tot']


z_tot = ff2['ZWARN'] != 999999
z_suc =ff2['ZWARN']==0
z_suc&=ff2['DELTACHI2']>40
#print(len(ff2[z_suc]),len(ff2[z_tot]))
print("zsuccess rate for BGS=",len(ff2[z_suc])/len(ff2[z_tot]))
cat2 = Table(ff2[z_tot])

fiberstats2 = Table()
fiberstats2['FIBER'], fiberstats2['n_tot'] = np.unique(ff2['FIBER'][z_tot], return_counts=True)
#fiberstats.sort('n_tot')

tt2 = Table()
tt2['FIBER'], tt2['n_suc'] = np.unique(ff2['FIBER'][z_suc], return_counts=True)
fiberstats2 = join(fiberstats2, tt2, keys='FIBER', join_type='outer').filled(0)
fiberstats2 = join(fiberstats2,full, keys='FIBER',join_type='outer').filled(0)
#fiberstats2['frac_suc'] = fiberstats2['n_suc']/fiberstats2['n_tot']


fstats_comb = Table()
fstats_comb['Fiber']=np.arange(5000)
fstats_comb['n_tot']=np.arange(5000)
fstats_comb['n_suc']=np.arange(5000)
for fiber in fstats_comb['Fiber']:
    m1=fiberstats1['FIBER']==fiber
    m2=fiberstats2['FIBER']==fiber
    fstats_comb['n_tot'][fiber] = fiberstats1['n_tot'][m1]+fiberstats2['n_tot'][m2]
    fstats_comb['n_suc'][fiber] = fiberstats1['n_suc'][m1]+fiberstats2['n_suc'][m2]

mask0= fstats_comb['n_tot']>1
fstats_comb=fstats_comb[mask0]
fstats_comb['frac_suc']=fstats_comb['n_suc']/fstats_comb['n_tot']
#fstats_comb 

error_floor = True

n, p = fstats_comb['n_tot'].copy(), fstats_comb['frac_suc'].copy()
if error_floor:
    p1 = np.maximum(1-p, 1/n)  # error floor
else:
    p1 = p
fstats_comb['frac_suc_err'] = np.clip(np.sqrt(n * p * (1-p))/n, np.sqrt(n * p1 * (1-p1))/n, 1)

#print("Removed fibers for having only 1 obs:\n",fstats_comb['FIBER'][ntotmask])
mean = np.sum(fstats_comb['n_suc'])/np.sum(fstats_comb['n_tot'])
fstats_comb['check'] =(mean - fstats_comb['frac_suc'])/fstats_comb['frac_suc_err']
fstats_comb.sort('frac_suc')
#fstats_comb



#mean = np.sum(fstats_comb['n_suc'])/np.sum(fstats_comb['n_tot'])
n = 3
maskcheck = fstats_comb['check']>n
fstats_comb
np.savetxt(basedir+'/'+survey+'/LSS/'+specver+'/LSScats/'+version+"/lrg+bgs_"+str(n)+"sig_bad_fibers.txt",fstats_comb[maskcheck]['Fiber'],fmt='%i')