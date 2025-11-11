import pandas as pd
import os
import glob
from os import path
import shutil

def rename(dir_in, clean_dir = False):
    """This function renames UAVSAR data in a directory containing csv file of annotation to a more intuitive name.
        The format will be sitename_date-of-first-acquisition_date-of-second-acquisition_XXXpolarization_filetype(coh/amp/hgd).
        The renamed files are stored in a new directory called renamed.

    Args:
        dir_in (_type_): path to the directory containing the tiff files to be renamed
        clean_dir (bool, optional): wether to delete the old files or not. Defaults to False.
    """    

    #check if crop directory exists
    dir_out = dir_in + '/renamed/'
    if not os.path.exists(dir_out):
        os.makedirs(dir_out)

    #read the metadata from the csv file
    metadata = pd.read_csv(glob.glob(dir_in + '/*grd.csv')[0]) #it gives a list, so select the only item in the list

    #grab the start time of first acquisition for pass 1
    date1 = (metadata.loc[0, 'start time of acquisition for pass 1']).split()[0]

    #grab the start time of acquisition for pass 2
    date2 = (metadata.loc[0, 'start time of acquisition for pass 2']).split()[0]


    #loop through the files
    for tiff in glob.glob(dir_in + '/*grd.tiff'):

        #grab the site name from the tiff sting
        file_name = (tiff.split('/')[-1]).split('_')[0]

        #grab the last two sets of strings from the tiff name
        set2 = (tiff.split('/')[-1]).split('_')[-2]
        set1 = (tiff.split('/')[-1]).split('_')[-1]
        new_name = dir_out + file_name + '_' + date1 + '_' + date2 + '_' + set2 + '_' + set1

        if clean_dir == False:
            shutil.copy(tiff, new_name)
        elif clean_dir == True:
            shutil.move(tiff, new_name)