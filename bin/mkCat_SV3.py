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
parser.add_argument("--cuttar", help="cut targets to SV3 tiles",default='y')
parser.add_argument("--cutran", help="cut randoms to SV3 tiles",default='y')
parser.add_argument("--vis", help="make a plot of data/randoms on tile",default='n')
parser.add_argument("--xi", help="run pair-counting code",default='n')
parser.add_argument("--ranmtl", help="make a random mtl file for the tile",default='n')
parser.add_argument("--rfa", help="run randoms through fiberassign",default='y')
parser.add_argument("--fulld", help="make the 'full' catalog containing info on everything physically reachable by a fiber",default='y')
parser.add_argument("--fullr", help="make the random files associated with the full data files",default='y')
parser.add_argument("--clus", help="make the data/random clustering files; these are cut to a small subset of columns",default='y')
parser.add_argument("--nz", help="get n(z) for type and all subtypes",default='y')



args = parser.parse_args()
print(args)

type = args.type
basedir = args.basedir
version = args.version

ctar = False
if args.cuttar == 'y':
    ctar = True
cran = False
if args.cutran == 'y':
    cran = True
docatplots = False
if args.vis == 'y':
    docatplots = True
doclus = False
if args.xi == 'y':    
    doclus = True
mkranmtl = False
if args.ranmtl == 'y':
    mkranmtl = True
runrfa = True#run randoms through fiberassign
if args.rfa == 'n':
    runrfa = False
mkfulld = True #make the 'full' catalog containing info on everything physically reachable by a fiber
if args.fulld == 'n':
    mkfulld = False
mkfullr = True #make the random files associated with the full data files
if args.fullr == 'n':
    mkfullr = False
mkclus = True #make the data/random clustering files; these are cut to a small subset of columns
if args.clus == 'n':
    mkclus = False
mknz = True #get n(z) for type and all subtypes
if args.nz == 'n':
    mknz = False


if type == 'BGS_ANY':
    pr = 'BRIGHT'
    pdir = 'bright'
else:
    pr = 'DARK'
    pdir = 'dark'



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

wp = np.isin(mtld['TILEID'],tiles['TILEID']) #we want to consider MTL done tiles that correspond to the SV3 tile file
mtld = mtld[wp]



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
        fht = fitsio.read_header('/global/cfs/cdirs/desi/target/fiberassign/tiles/trunk/0'+str(tile)[:2]+'/fiberassign-0'+str(tile)+'.fits.gz')
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


runfa = False
mkdtiles = False
combd = False
combr = False
mkfulldat = False
mkfullran = False
mkclusdat = False
mkclusran = False

if ctar:
    tard = read_targets_in_tiles(mdir,tiles,mtl=True,isodate='2021-04-06T00:00:00') #this date should be after initial creation and before 1st update
    print('read in mtl targets')
    print('should be 0 '+str(np.unique(tard['NUMOBS'])))
    minr = np.min(tard['RA'])-1
    maxr = np.max(tard['RA'])+1
    mind = np.min(tard['DEC'])-1
    maxd = np.max(tard['DEC'])+1

    tardi = inflate_ledger(tard,tdir)
    tardi = Table(tardi)
    tardi.write(sv3dir+pdir+'_targets.fits',overwrite=True,format='fits')
    print('wrote inflated ledger target file to '+sv3dir+pdir+'_targets.fits')
    del tardi
    del tard

if cran:
    dirrt='/global/cfs/cdirs/desi/target/catalogs/dr9/0.49.0/randoms/resolve/'
    for ii in range(rm,rx):
        ranf = fitsio.read(dirrt+'/randoms-1-'+str(ii)+'.fits')
        print(len(ranf))
        if cuttar:
            wp = ranf['RA'] > minr
            wp &= ranf['RA'] < maxr
            wp &= ranf['DEC'] > mind
            wp &= ranf['DEC'] < maxd
            ranf = ranf[wp]
            print(len(ranf))                
        wi = is_point_in_desi(tiles, ranf["RA"], ranf["DEC"])
        ranf = ranf[wi]
        fitsio.write(sv3dir+'random'+str(i)+'/alltilesnofa_'+pdir+'.fits',ranf,clobber=True)

if mktileran:
    ct.randomtiles_allSV2(ta,imin=rm,imax=rx)
    
if runfa:
    for ii in range(0,len(mtld)):
        tile = mtld['TILEID'][ii]
        fbah = fitsio.read_header('/global/cfs/cdirs/desi/target/fiberassign/tiles/trunk/0'+str(tile)[:2]+'/fiberassign-0'+str(tile)+'.fits.gz')
        dt = fbah['FA_RUN']
        ttemp = Table(ta[ii])
        ttemp['OBSCONDITIONS'] = 516
        ttemp['IN_DESI'] = 1
        ttemp.write('tiletemp.fits',format='fits', overwrite=True)
        for i in range(rm,rx):
            testfbaf = randir+str(i)+'/fba-0'+str(tile)+'.fits'
            if os.path.isfile(testfbaf):
                print('fba file already made')
            else:   
                
                fa.getfatiles(randir+str(i)+'/tilenofa-'+str(tile)+'.fits','tiletemp.fits',dirout=randir+str(i)+'/',dt = dt)

if mkdtiles:
    for tile,zdate in zip(mtld['TILEID'],mtld['ZDATE']):
        ffd = dirout+type+str(tile)+'_full.dat.fits'
        tspec = ct.combspecdata(tile,zdate)
        pdict,goodloc = ct.goodlocdict(tspec)
        fbaf = '/global/cfs/cdirs/desi/target/fiberassign/tiles/trunk/0'+str(tile)[:2]+'/fiberassign-0'+str(tile)+'.fits.gz'
        wt = ta['TILEID'] == tile
        tars = read_targets_in_tiles(mdir,ta[wt],mtl=True)
        tars = inflate_ledger(tars,tdir)
        tars = tars[[b for b in list(tars.dtype.names) if b != 'Z']]
        tars = tars[[b for b in list(tars.dtype.names) if b != 'ZWARN']]
        tars = tars[[b for b in list(tars.dtype.names) if b != 'PRIORITY']]
        tars = join(tars,tspec,keys=['TARGETID'],join_type='left')
        tout = ct.gettarinfo_type(fbaf,tars,goodloc,tarbit,pdict)
        #tout = join(tfa,tspec,keys=['TARGETID','LOCATION'],join_type='left') #targetid should be enough, but all three are in both and should be the same
        print(tout.dtype.names)
        wz = tout['ZWARN']*0 == 0
        wzg = tout['ZWARN'] == 0
        print('there are '+str(len(tout[wz]))+' rows with spec obs redshifts and '+str(len(tout[wzg]))+' with zwarn=0')
        
        tout.write(ffd,format='fits', overwrite=True) 
        print('wrote matched targets/redshifts to '+ffd)
        #logf.write('made full data files\n')

if combd:
    print(len(mtld['TILEID']))
    ct.combtiles(mtld['TILEID'],dirout,type)    


if combr:
    print(len(mtld['TILEID']))
    for i in range(rm,rx):
        ct.combran(mtld,i,randir)
        
        
if mkfulldat:
    ct.mkfulldat(dirout+type+'Alltiles_full.dat.fits',imbits,tdir)
    #get_tilelocweight()
    #logf.write('ran get_tilelocweight\n')
    #print('ran get_tilelocweight\n')

if mkfullran:
    for ii in range(rm,rx):
        outf = dirout+type+'Alltiles_'+str(ii)+'_full.ran.fits'
        ct.mkfullran(randir,ii,imbits,outf)
    #logf.write('ran mkfullran\n')
    #print('ran mkfullran\n')

#needs to happen before randoms so randoms can get z and weights
if mkclusdat:
    ct.mkclusdat(dirout+type+'Alltiles_')
    #logf.write('ran mkclusdat\n')
    #print('ran mkclusdat\n')

if mkclusran:
    for ii in range(rm,rx):
        ct.mkclusran(dirout+type+'Alltiles_',ii)
    #logf.write('ran mkclusran\n')
    #print('ran mkclusran\n')
    
if mkNbar:
    e2e.mkNbar(target_type,program,P0=P0,omega_matter=omega_matter,truez=truez)
    logf.write('made nbar\n')
    print('made nbar\n')

if fillNZ:
    e2e.fillNZ(target_type,program,P0=P0,truez=truez)   
    logf.write('put NZ and weight_fkp into clustering catalogs\n')    
    print('put NZ and weight_fkp into clustering catalogs\n')
        