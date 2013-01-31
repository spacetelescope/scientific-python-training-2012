#!/usr/bin/env python
from __future__ import print_function
import os,sys


import pyfits
from pyraf import iraf
from iraf import noao,digiphot,daophot

import numpy as np
import matplotlib.pyplot as plt
from tempfile import mkstemp
import aperphot

__version__ = "1.0 (2012 Jan 30)"
__author__ = "Megan Sosey"


def apercor(image,plotname='aperture_correction.pdf',save=False):

    """
	    Megan Sosey, January 2013
	    Written as an example script to run aperture photometry on the star at the center of the image
        that is specified. You can make this more general by prompting for a specific x,y location along
        with the image name (an exercise left to you).

        ****these parameters are setup up specificially to deal with a tiny tim type model image.*****
            TinyTim has normalized flux values and no sky

        INPUT: 

            image [string]: the input image you want to use
            plotname [string]: the name of the output plot file
            save [bool]: save the output photometry file?

        OUTPUT:
            output plots in PDF form with information printed in the plots
            optional: the output photometry results file

        FUNCTION:

	        Run photometry on the given star, at the center of the image and save a plot of the 
            flux values at different radii to compute an aperture correction.

            also report the FWHM of the star


    """
    if not os.access(image,os.F_OK):
        raise IOError("Unable to access input image: %s"%(image))
        
    
    aperphot.set_daopars(1.) #nasic pars we want, set gain to 1
    data=pyfits.getdata(image)
    xsize,ysize=data.shape
    
    starfile,cooname=mkstemp(suffix='coo',dir='./') #temp location file in current directory
    magfile=image + ".phot"

    of=open(cooname,'w')
    of.write(("%i\t%i\n")%(xsize/2,ysize/2))
    of.close()
    #set up the photpars to do a range of apertures, we'll go out half the size of the image
    aperlist=list() 
    for i in range(1,xsize/2,4):
        aperlist.append(str(i))
    
    alist= ",".join(aperlist)   
        
    #pick a sky annulus towards the edge of the image
    aperphot.do_phot(image,cooname, aper=alist, sky_annulus=xsize-20, width_sky=3.,zeropoint=25.)
    
    
    #read in the output file, but in this case I'm going to use daophot.pdump to directly pull the info I want
    iraf.daophot.pdump(magfile,fields="xcen,ycen,flux",expr="yes",header="no",parameters="no")
    
    #make a plot of the measure flux as a function of radius (distance from the center)
    plot(magfile)
    
    
    
def readaper(filename):
    """read in a phot file where apertures have been saved for a single star"""
    
    if not os.access(filename,os.F_OK):
        raise IOError("Unable to access input file: %s"%(filename))
   
    
    #read in the file
    infile=open(filename,'r')
    lines=infile.readlines()
    infile.close()
    
    #I know there are 78 header lines
    data=lines[79:]
    
    #now grab the data I want and reformat for plotting
    rapert=list()
    flux=list()
    for line in data:
        rapert.append(float(line.split()[0]))
        flux.append(float(line.split()[1]))
        
    
    return (rapert,flux)
    

def plot(magfile):

    rapert,flux = readaper(magfile)
    
    plt.ioff() #turn off interactive so plots dont pop up 
    plt.figure(figsize=(8,10)) #this is in inches
    
    
    plt.xlabel('radius')
    plt.ylabel('total flux')
    plt.plot(rapert,flux,'bx')
    plt.title(magfile,{'fontsize':10})

    plt.title("Total flux collected per aperture")
        
    outfile=magfile+".pdf"
    plt.savefig(outfile)
    print(("saved output figure to %s")%(outfile))
