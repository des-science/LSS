#right now, requires source /project/projectdirs/desi/software/desi_environment.sh master
from astropy.table import Table
import numpy as np
import os
import argparse
from desitarget.targetmask import zwarn_mask

parser = argparse.ArgumentParser()
parser.add_argument("--night", help="use this if you want to specify the night, rather than just use the last one",default=None)
args = parser.parse_args()

#open exposures file
exps = Table.read('/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/exposures.ecsv')
#remove the rows that don't have night so that next lines work
sel = exps['NIGHT'] != 'None'
#check if tileid are in main
tlm = Table.read('/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-main.ecsv')
wd = tlm['FAPRGRM'] == 'dark' #only select dark tiles for LRG check
tlm = tlm[wd]
sel &= np.isin(exps['TILEID'],tlm['TILEID'])
exps = exps[sel]

if args.night == None:
    #find the most recent night
    maxn = np.max(exps['NIGHT'].astype(int))
else:
    maxn = int(args.night)  
seln = exps['NIGHT'].astype(int) == maxn
#get the list of tileids observed on the last night
tidl = np.unique(exps[seln]['TILEID'])

print('looking at LRG redshift results from the night '+str(maxn))
print('the tileids are:')
print(tidl)


#one list for each petal for total targets
gz = np.zeros(10)
tz = np.zeros(10)

zdir = '/global/cfs/cdirs/desi/spectro/redux/daily/tiles/cumulative/'

for tid in tidl:
    for pt in range(0,10):
        zmtlf = fitsio.read(zdir+args.night+'/zmtl-'+str(pt)+'-'+str(tid)+'-thru'+args.night+'.fits')
        nodata = zmtlf["ZWARN"] & zwarn_mask["NODATA"] != 0
        num_nod = np.sum(nodata)
        print('looking at petal '+str(pt)+' on tile '+str(tid))
        print('number with no data '+str(num_nod))
        badqa = zmtlf["ZWARN"] & zwarn_mask.mask("BAD_SPECQA|BAD_PETALQA") != 0
        num_badqa = np.sum(badqa)
        print('number with bad qa '+str(num_badqa))
        nomtl = nodata | badqa
        wfqa = ~nomtl
        wlrg = (zmtlf['DESI_TARGET'] & 1) > 0
        zlrg = zmtlf[wfqa&wlrg]
        if len(zlrg) > 0:
            wzwarn = zmtlf['ZWARN'] == 0
            gzlrg = zmtlf[wzwarn&wlrg]
            print('The fraction of good LRGs is '+str(len(gzlrg)/len(zlrg))+' for '+str(len(zlrg))+' considered spectra')
            gz[pt] += len(gzlrg)
            tz[pt] += len(zlrg)
        else:
            print('no good lrg data')   
        

tzs = gz/tz
print('the total fraction of good LRG z per petal for the night is:')
print(tzs)