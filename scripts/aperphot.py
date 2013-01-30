#!/usr/bin/env python
import os,sys

#watch out for older versions of astropy without the format read fix
from astropy.io import ascii
from astropy import table

import pyfits
from pyraf import iraf
from iraf import noao,digiphot,daophot,ptools


#needed for daophot if no login.cl in current directory
#you should probably run from a directory with login.cl
#anyways if you are going to import iraf tasks

from stsci import tools
tools.irafglobals.userid='yoda'
 
import numpy as np
from glob import glob

import matplotlib.pyplot as plt
from optparse import OptionParser

"""
	Megan Sosey, December 2012
	Written as an example script to run aperture photometry on any given image
    
    This has some bells and whistles as examples of things you might like to try
    
    INPUT: 
    
        inputImage [string]: the input image you want to use
        aper:  [int]: the aperture for photometry
        sky_annulus [int]: the starting pixel for sky
        width_sky   [int]: the width of the sky annulus in pixels
        plots       [bool]: save plots of the results to disk

    OUTPUT:
        possible plots in PDF form
        the list of object coordinates
        the output photometry results file
        
    FUNCTION:
    		
        Run daofind on the input image
	    Run photometry on the given stars, for the CURRENT image, this could be a subtracted image with extra stars in it
		
	    Dump the resulting star list and phot file
		
	    REM:     sharp is large positive for blended doubles 
		         close to 0 for stars
			     large negative for crs and blemishes
	
    

"""

__version__ = "1.0 (2012 Jan 30)"
__author__ = "Megan Sosey"


def message(something):
	"""This is just for displayin simple, short messages that stickout """
	
	print
 	print "="*len(something)
	print something
	print "="*len(something)
	print


def run(image,aper="4.",sky=8., width=3., plots=False):
    """
    Call this to perform all the following fucntions
    
    Parameters
        image:  string, name of the image
        aper:   string, size of the photometry aperture(s)
        sky:    float, where to start the sky aperture
        width:  float, how wide should the sky annulus be
        plots:  bool, save plots of the results for quicklook
        
        
    example:
    
    aperphot.run('myimage.fits',aper="2.")
    
    """
    
    message("Setting up photometry for %s"%(image))
    
    #make sure that we are using data we are prepared for, you can write other functions
    #to deal with this or help set alternate parameters. An ideal setup might involve a class structure
    #but we'll keep it more simple here
    instrument=pyfits.getval(image,"INSTRUME")
    if "NICMOS" not in instrument:
        print "Program only valid for NICMOS images, check inputs"
        return IOError     
        
    #calculate the zeropoint from the header, these are set for NICMOS
    #you could make functions for different instruments here
    photfnu=pyfits.getval(image,"PHOTFNU")
    abzpt=-2.5* np.log10(photfnu*1.0*1e-23) -48.6
    
    print "zeropoint: %f"%(abzpt)

	#calculate the effective gain for the image in NICMOS
    exp=float(pyfits.getval(image,'EXPTIME'))
    hgain=float(pyfits.getval(image,'ADCGAIN'))
    epadu=hgain*exp # to get the errors better, nicmos is actually dn/s

    print "Setting effective gain = %f "%(epadu) #to make sure errors and chi are computed as best as possible


    set_daopars(epadu)
    
    coord_list=find_objects(image)
    
    photometry = do_phot(image, coord_list, aper=aper, sky_annulus=sky, width_sky=width, zeropoint=abzpt)
    
    if plots: plotphot(photometry)
    
    
def set_daopars(epadu):
    """
    Set all the iraf parameter files for daophot
    
    """
    instrument="NICMOS"
    #change this as necessary or setup a functional input for the important factors
    fwhm = 3.5 
    readnoise = 26.
    
    print  "Setting DAOpars to %s defaults..."%(instrument)
    print "\t Using fwhmpsf: %f"%(fwhm)
        
    #set up the data and phot parameters we want to use
    #I'm setting them all explicitly here, you could also
    #unlearn the parameter tasks to get the defaults and then 
    #hard set just a few
    iraf.daophot.phot.verbose="no"
    iraf.daophot.phot.interactive="no"
    iraf.daophot.phot.verify="no"
    
    iraf.datapars.scale=1.
    iraf.datapars.fwhmpsf=fwhm
    iraf.datapars.emiss="yes"
    iraf.datapars.sigma=0.
    iraf.datapars.datamin=-0.001
    iraf.datapars.datamax="INDEF"
    iraf.datapars.noise="poisson"
    iraf.datapars.ccdread=""
    iraf.datapars.gain=""
    iraf.datapars.readnoi=readnoise
    iraf.datapars.epadu=epadu
    iraf.datapars.airmass=""
    iraf.datapars.filter="filter"
    iraf.datapars.itime=1.

    iraf.centerpars.calgo="centroid"
    iraf.centerpars.cbox=7.
    iraf.centerpars.cthres=0
    iraf.centerpars.minsn=1.
    iraf.centerpars.cmaxiter=10
    iraf.centerpars.maxshift=1.
    iraf.centerpars.clean="no"
    iraf.centerpars.rclean=1.
    iraf.centerpars.rclip=2.
    iraf.centerpars.kclean=3.
    iraf.centerpars.mkcenter="no"

    iraf.daophot.daopars.function="auto"
    iraf.daophot.daopars.varorder=1
    iraf.daophot.daopars.nclean=0
    iraf.daophot.daopars.sat="no"
    iraf.daophot.daopars.matchrad=3.
    iraf.daophot.daopars.psfrad=15
    iraf.daophot.daopars.fitrad=3.4
    iraf.daophot.daopars.recenter="yes"
    iraf.daophot.daopars.fitsky="yes"
    iraf.daophot.daopars.groups="yes"
    iraf.daophot.daopars.sannu=8
    iraf.daophot.daopars.wsann=15.
    iraf.daophot.daopars.flaterr=0.75
    iraf.daophot.daopars.proferr=2.5
    iraf.daophot.daopars.maxiter=50
    iraf.daophot.daopars.clipexp=4
    iraf.daophot.daopars.clipra=2.5
    iraf.daophot.daopars.mergerad="INDEF"
    iraf.daophot.daopars.critsn=1.
    iraf.daophot.daopars.maxgroup=30
    iraf.daophot.daopars.text="yes"


def find_objects(inputImage):
    """
    Find the objects in the field
    use DAOfind 
    """

    output_locations= inputImage  + ".stars" #best to set this if you're scripting
    
    #check if a file already exists and remove it
    if os.access(output_locations,os.F_OK):
        print "Removing previous star location file"
        os.remove(output_locations)
        
    
    #set up some finding parameters, you can make this more explicit
    iraf.daophot.findpars.threshold=3.0 #3sigma detections only
    iraf.daophot.findpars.nsigma=1.5 #width of convolution kernal in sigma
    iraf.daophot.findpars.ratio=1.0 #ratio of gaussian axes
    iraf.daophot.findpars.theta=0.
    iraf.daophot.findpars.sharplo=0.2 #lower bound on feature
    iraf.daophot.findpars.sharphi=1.0 #upper bound on feature
    iraf.daophot.findpars.roundlo=-1.0 #lower bound on roundness
    iraf.daophot.findpars.roundhi=1.0 #upper bound on roundness
    iraf.daophot.findpars.mkdetections="no"
    
    #assume the science extension
    sci="[SCI,1]"
    message(inputImage + sci)
    iraf.daofind(image=inputImage+sci,output=output_locations,interactive="no",verify="no",verbose="no")

    print "Saved output locations to %s"%(output_locations)
    
    return output_locations #return the name of the saved file
    
def do_phot(inputImage, coord_list, aper="4.", sky_annulus=8., width_sky=3.,zeropoint=25.):
    """
    perform aperture photmoetry on the input image at the specified locations
    
    **aper is a string so that you can call phot with multiple apertures**
    """
    print "\t Phot aperture: %s pixels"%(aper)
    print "\t Sky Annulus: %i -> %i pixels"%(sky_annulus,sky_annulus+width_sky)

    output = inputImage+ ".phot" #can be anything you like
    if os.access(output,os.F_OK):
        print  "Removing previous photometry file" 
        os.remove(output)
    print "\t Saving output files as %s"%(output)

    iraf.photpars.weighting="constant"
    iraf.photpars.aperture=aper
    iraf.photpars.zmag=zeropoint
    iraf.photpars.mkapert="no"

    iraf.daophot.phot.interactive="no"
    iraf.daophot.phot.verify="no"
    iraf.daophot.phot.verbose="no"
    
    iraf.fitskypars.salgo="centroid"
    iraf.fitskypars.annu=sky_annulus
    iraf.fitskypars.dannu=width_sky
    iraf.fitskypars.skyval=0
    iraf.fitskypars.smaxi=10
    iraf.fitskypars.sloc=0
    iraf.fitskypars.shic=0
    iraf.fitskypars.snrej=50
    iraf.fitskypars.slorej=3.
    iraf.fitskypars.shirej=3.
    iraf.fitskypars.khist=3
    iraf.fitskypars.binsi=0.1

    inputImage =inputImage + "[SCI,1]" #assumed, might be risky
    iraf.phot.coords=coord_list
    iraf.phot.output=output
    iraf.daophot.phot.verify="no"
    iraf.daophot.phot.interactive="no"
    iraf.daophot.phot.radplots="no"
    
    iraf.daophot.phot(inputImage,coords=coord_list,verbose="no",verify="no",interactive="no") 
    return output


def plotphot(photdata,ftype="pdf"):
    """
    neato phot plots from the output files
    use the astropy library to read the input files
    make sure you have astropy0.2 or later installed or it might fail to read correctly
    """
    print photdata
    outfile=photdata + "." + ftype

    #read the ascii table into an astropy.table
    reader=ascii.Daophot()
    photfile = reader.read(photdata)
    

    #remove the points that had issues
    noerror=np.where(photfile[:]['PERROR'] == 'NoError')
    goodphot=photfile[noerror[0][:]]
    indef=np.where(goodphot["MAG"] != "INDEF")
    phot=goodphot[indef[0][:]]



    plt.ioff() #turn off interactive so plots dont pop up 
    plt.figure(figsize=(8,10)) #this is in inches
    
    
    mag=phot["MAG"].astype(np.float)
    merr=phot["MERR"].astype(np.float)

    #mag vs merr
    plt.subplot(221)
    plt.xlabel('MAG')
    plt.ylabel('MERR')
    plt.plot(mag,merr,'bx')
    plt.title(photdata,{'fontsize':10})

    #magnitude histogram
    plt.subplot(222)
    plt.xlabel('mag')
    plt.ylabel('Number')
    plt.hist(mag,10)
    plt.xlim(19,29)
    
    #overplot the cummulative curve
    normHist, bins,patches = plt.hist(mag, bins=10, normed=False)
    plt.title('Mag distribution',{'fontsize' : 10})

    xsh=phot["XSHIFT"].astype(np.float)
    ysh=phot["YSHIFT"].astype(np.float)
    #xshift and yshifts, just to see
    plt.subplot(223)
    plt.xlabel('XSHIFT')
    plt.ylabel('YSHIFT')
    plt.plot(xsh,ysh,'bx')
    plt.title('Xshift vs Yshift of centers',{'fontsize':10})
    
    #a quick reference plot of the image and starlocations
    x=phot["XCENTER"].astype(np.float)
    y=phot["YCENTER"].astype(np.float)
    imname=phot["IMAGE"][0].split("[")[0]#assume all from 1 image, and remove extension (careful here)
    image=pyfits.getdata(imname)    
    plt.subplot(224)
    plt.xlabel('X')
    plt.ylabel('Y')
    plt.plot(x,y,'ko',mfc="None")
    zero=np.where(image <= 0)
    image[zero]=0.999
    plt.imshow(np.log10(image),cmap=plt.cm.gray)
    plt.title('Total Non-error Stars: %i'%(len(phot)),{'fontsize':10})
    
    plt.tight_layout()
    

    plt.savefig(outfile)
    print "saved output figure to %s"%(outfile)
    
def plotfind(findata,ftype="pdf"):
    """
    plot just the data from the stellar locations file
    """

    outfile=findata+"."+ftype

    #read the ascii table into an astropy.table
    reader=ascii.Daophot()
    photfile = reader.read(findata)
    

    #remove the points that had issues
    noerror=np.where(photfile[:]['PERROR'] == 'NoError')
    goodphot=photfile[good[0][:]]
    indef=np.where(goodphot["MAG"] != "INDEF")
    phot=goodphot[indef[0][:]]



    plt.figure(figsize=(8,10)) #this is in inches
    plt.title('Total Stars Detected %i'%(len(phot)))
    
    mag=phot["MAG"].astype(np.float)
    merr=phot["MERR"].astype(np.float)

    #plots from the finder program
    #sharpness histogram from the detection file
    plt.subplot(222)
    plt.xlabel('Sharpness')
    plt.ylabel('Number')
    hist,bins,p=plt.hist(sharp,10,normed=False)
    plt.title('Detection Types',{'fontsize':10})
    #plt.legend(['Stars','Blends','Blemish'],loc='upper left')
    delta=max(hist)/len(bins)
    yy=max(hist)-delta
    plt.text(bins[0],yy,'Stars at zero',{'color' :'black', 'fontsize' : 10})
    plt.text(bins[0],yy-delta*1.5,'Blends Positive',{'color' :'black', 'fontsize' : 10})
    plt.text(bins[0],yy-delta*2.5,'Blemish Negative',{'color': 'black','fontsize': 10})


    #chi  relation
    plt.subplot(224)
    plt.xlabel('chi')
    plt.ylabel('mag')
    #plt.hist(chi<2,10,normed=False)
    u=np.where(sharp < 1.5)
    uu=np.where(sharp[u] > 0.5)
    schi=chi[uu]
    smag=mag[uu]
    plt.plot(schi,smag,'bx')
    plt.xlim(0,2)
    plt.title('CHI-ball for stars (0.5<sharp>1.5)',{'fontsize': 10})
    plt.savefig(outfile)

    return ofile

	


if __name__ == "__main__":  #this tells the os what to do if you called the script from a command shell


    #parse the commandline options
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-i","--input",dest="inputImage",default="none",type="string",
	    help="The input image to do phot on",metavar="INPUTLIST")

    parser.add_option("-a", "--aper",dest="aper",default="4.",type="string",
        help="What aperture to do the photometry at (or string sep comma list of apers)")

    parser.add_option("-s","--skyannulus",dest="skyannulus",default=8,type="int",
        help="The pixel distance from center for sky annulus")

    parser.add_option("-w","--skywidth",dest="skywidth",default=3,type="int",
        help="The width of the sky annulus")

    parser.add_option("-p","--plots",dest="plots",default=False,action="store_true",
	    help="Save plots describing the resulting photometry")



    (options, args)  = parser.parse_args()


    if(not(os.access(options.inputImage,os.F_OK))):
	    print "Unable to access input Image: ",options.inImage
	    sys.exit(0)

    run(options.inputImage,options.aper,options.skyannulus,options.skywidth,options.plots)
    print "\nPhotometry is awesome.\n\n"
	
		
	
	

