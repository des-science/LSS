#standard python
import sys
import os
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
from desitarget.io import read_targets_in_tiles
from desitarget.mtl import inflate_ledger
from desimodel.footprint import is_point_in_desi

sys.path.append('../py') #this requires running from LSS/bin, *something* must allow linking without this but is not present in code yet

#from this package
#try:
import LSS.SV3.cattools as ct
#except:
#    print('import of LSS.mkCat_singletile.cattools failed')
#    print('are you in LSS/bin?, if not, that is probably why the import failed')   
import LSS.mkCat_singletile.fa4lsscat as fa

parser = argparse.ArgumentParser()
parser.add_argument("--type", help="tracer type to be selected")
parser.add_argument("--basedir", help="base directory for output, default is CSCRATCH",default=os.environ['CSCRATCH'])
parser.add_argument("--version", help="catalog version; use 'test' unless you know what you are doing!",default='test')
parser.add_argument("--cutran", help="cut randoms to SV3 tiles",default='n')
parser.add_argument("--ranmtl", help="make a random mtl file for the tile",default='y')
parser.add_argument("--rfa", help="run randoms through fiberassign",default='y')
parser.add_argument("--combr", help="combine the random tiles together",default='y')
parser.add_argument("--fullr", help="make the random files associated with the full data files",default='y')
parser.add_argument("--clus", help="make the data/random clustering files; these are cut to a small subset of columns",default='y')
parser.add_argument("--nz", help="get n(z) for type and all subtypes",default='y')



args = parser.parse_args()
print(args)

type = args.type
basedir = args.basedir
version = args.version

cran = False
if args.cutran == 'y':
    cran = True

mkranmtl = False
if args.ranmtl == 'y':
    mkranmtl = True
runrfa = True#run randoms through fiberassign
if args.rfa == 'n':
    runrfa = False


mkfullr = True #make the random files associated with the full data files
if args.fullr == 'n':
    mkfullr = False
mkclus = True #make the data/random clustering files; these are cut to a small subset of columns
mkclusran = True
if args.clus == 'n':
    mkclus = False
    mkclusran = False
combr = True
if args.combr == 'n':
    combr = False   


if type == 'BGS_ANY':
    pr = 'BRIGHT'
    pdir = 'bright'
else:
    pr = 'DARK'
    pdir = 'dark'

pd = pdir

mdir = '/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/mtl/sv3/'+pdir+'/' #location of ledgers
tdir = '/global/cfs/cdirs/desi/target/catalogs/dr9/0.57.0/targets/sv3/resolve/'+pdir+'/' #location of targets
mtld = Table.read('/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/mtl/mtl-done-tiles.ecsv') #log of tiles completed for mtl
tiles = Table.read('/global/cfs/cdirs/desi/survey/ops/surveyops/trunk/ops/tiles-sv3.ecsv')
imbits = [1,5,6,7,8,9,11,12,13]

#share basedir location '/global/cfs/cdirs/desi/survey/catalogs'
sv3dir = basedir +'/SV3/LSS/'

from desitarget.sv3 import sv3_targetmask

tarbit = int(np.log2(sv3_targetmask.desi_mask[type]))

wp = tiles['PROGRAM'] == pr
tiles = tiles[wp]
print(len(tiles))

wp = np.isin(mtld['TILEID'],tiles['TILEID']) #we want to consider MTL done tiles that correspond to the SV3 tile file
mtld = mtld[wp]
print(len(mtld))



if not os.path.exists(sv3dir+'/logs'):
    os.mkdir(sv3dir+'/logs')
    print('made '+sv3dir+'/logs')

if not os.path.exists(sv3dir+'/LSScats'):
    os.mkdir(sv3dir+'/LSScats')
    print('made '+sv3dir+'/LSScats')

dirout = sv3dir+'LSScats/'+version+'/'
if not os.path.exists(dirout):
    os.mkdir(dirout)
    print('made '+dirout)


randir = sv3dir+'random'
rm = 0
rx = 18
#logf.write('using random files '+str(rm)+ ' through '+str(rx)+' (this is python, so max is not inclusive)\n')
for i in range(rm,rx):
    if not os.path.exists(sv3dir+'random'+str(i)):
        os.mkdir(sv3dir+'random'+str(i))
        print('made '+str(i)+' random directory')


#construct a table with the needed tile information
if len(mtld) > 0:
    tilel = []
    ral = []
    decl = []
    mtlt = []
    fal = []
    obsl = []
    pl = []
    for tile,pro in zip(mtld['TILEID'],mtld['PROGRAM']):
        ts = str(tile).zfill(6)
        fht = fitsio.read_header('/global/cfs/cdirs/desi/target/fiberassign/tiles/trunk/'+ts[:3]+'/fiberassign-'+ts+'.fits.gz')
        tilel.append(tile)
        ral.append(fht['TILERA'])
        decl.append(fht['TILEDEC'])
        mtlt.append(fht['MTLTIME'])
        fal.append(fht['FA_RUN'])
        obsl.append(fht['OBSCON'])
        pl.append(pro)
    ta = Table()
    ta['TILEID'] = tilel
    ta['RA'] = ral
    ta['DEC'] = decl
    ta['MTLTIME'] = mtlt
    ta['FA_RUN'] = fal
    ta['OBSCON'] = obsl
    ta['PROGRAM'] = pl
else:
    print('no done tiles in the MTL')


def doran(ii):
    dirrt='/global/cfs/cdirs/desi/target/catalogs/dr9/0.49.0/randoms/resolve/'   
    if cran:
        ranf = fitsio.read(dirrt+'/randoms-1-'+str(ii)+'.fits')
        print(len(ranf))
        if ctar:
            wp = ranf['RA'] > minr
            wp &= ranf['RA'] < maxr
            wp &= ranf['DEC'] > mind
            wp &= ranf['DEC'] < maxd
            ranf = ranf[wp]
            print(len(ranf))                
        wi = is_point_in_desi(tiles, ranf["RA"], ranf["DEC"])
        ranf = ranf[wi]
        fitsio.write(sv3dir+'random'+str(ii)+'/alltilesnofa.fits',ranf,clobber=True)
        print('wrote '+sv3dir+'random'+str(ii)+'/alltilesnofa.fits')

    if mkranmtl:
        ct.randomtiles_allSV3(ta,imin=ii,imax=ii+1)
    
    if runrfa:
        print('DID YOU DELETE THE OLD FILES!!!')
        for it in range(0,len(mtld)):
    
			tile = mtld['TILEID'][it]
			ts = str(tile).zfill(6)
			fbah = fitsio.read_header('/global/cfs/cdirs/desi/target/fiberassign/tiles/trunk/'+ts[:3]+'/fiberassign-'+ts+'.fits.gz')
			dt = fbah['RUNDATE']
			ttemp = Table(ta[it])
			ttemp['OBSCONDITIONS'] = 516
			ttemp['IN_DESI'] = 1
			ttemp.write('tiletemp.fits',format='fits', overwrite=True)
			#for i in range(rm,rx):
			testfbaf = randir+str(ii)+'/fba-'+str(tile).zfill(6)+'.fits'
			if os.path.isfile(testfbaf):
				print('fba file already made')
			else:                   
				fa.getfatiles(randir+str(ii)+'/tilenofa-'+str(tile)+'.fits','tiletemp.fits',dirout=randir+str(ii)+'/',dt = dt)

 

    if combr:
        print(len(mtld['TILEID']))
        ct.combran(mtld,ii,randir,dirout,type,sv3_targetmask.desi_mask)
        
    if mkfullr:
        outf = dirout+type+'Alltiles_'+str(ii)+'_full.ran.fits'
        ct.mkfullran(randir,ii,imbits,outf,type)
    #logf.write('ran mkfullran\n')
    #print('ran mkfullran\n')


    if mkclusran:
        ct.mkclusran(dirout+type+'Alltiles_',ii)
    #logf.write('ran mkclusran\n')
    #print('ran mkclusran\n')
    
if __name__ == '__main__':
    from multiprocessing import Pool
    import sys
    #N = int(sys.argv[2])
    N = rx
    p = Pool(N)
    inds = []
    for i in range(0,N):
        inds.append(i)
    p.map(doran,inds)