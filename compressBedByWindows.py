#!/usr/bin/env python

import argparse
import subprocess
import tempfile
import sys
import shutil
import os
import pybedtools

parser = argparse.ArgumentParser(description= """
DESCRIPTION
    
    Compress a bed file by applying a sliding window with a grouping function
    to the score column (5th col).
    Ouput is sent to stdout and has columns:
    
        <chrom>  <window_start>  <window_end>  <groupedby_score>

    Input must be sorted, first three columns must be chrom, start, end. Additional
    columns other than the score column are ignored.

EXAMPLE    
    You have a bed file with position of CpGs (one per row), the score column is
    the percentage of Cs methylated. You want to summarize % methylation in windows
    of size 10kb sliding by 1kb:

    compressBedByWindows.py -i methylation.bed -w 10000 -s 1000
    
""", formatter_class= argparse.RawTextHelpFormatter)

parser.add_argument('--input', '-i',
                   required= True,
                   help='''BED file to compress or - to read from stdin.
Input must be SORTED by position, without header.

''')

parser.add_argument('--scoreColumn', '-c',
                   required= False,
                   default= 5,
                   type= int,
                   help='''Column index with the score to be summarized.
Default is 5, suitable for bed files. Use 4 for bedGraph files.

''')

parser.add_argument('--window_size', '-w',
                   required= True,
                   type= int,
                   help='''Window size to group features. This option passed to
bedtools makewindows.

''')

parser.add_argument('--step_size', '-s',
                   required= False,
                   default= None,
                   type= int,
                   help='''Step size to slide windows. This option passed to
bedtools makewindows. Default step_size= window_size (non-sliding windows)

''')

parser.add_argument('--ops', '-o',
                   required= False,
                   default= 'sum',
                   type= str,
                   help='''Operation to apply to the score column. Default: sum
This option passed to bedtools groupBy.

''')

parser.add_argument('--tmpdir',
                    required= False,
                    default= None,
                   help='''For debugging: Directory where to put the tmp output files.
By default the temp dir is fetched by tempfile.mkdtemp and will be deleted at the end.
With this option the tmp dir will not be deleted. tmpdir will be created if it doesn't
exist.

''')

args = parser.parse_args()

if args.step_size is None:
    args.step_size= args.window_size

if args.tmpdir is None:
    tmpdir= tempfile.mkdtemp(prefix= 'compressBedByWindows_')
else:
    tmpdir= args.tmpdir
    if not os.path.isdir(tmpdir) and not os.path.exists(tmpdir):
        os.makedirs(tmpdir)
    elif not os.path.isdir(tmpdir) and os.path.exists(tmpdir):
        sys.exit('Requested tmp dir %s is a file' %(tmpdir))
    else:
        pass        

basename= os.path.split(args.input)[1]

if args.input == '-':
    "Need to write stream to file since we need it twice"
    inputBed= os.path.join(tmpdir, 'streamInput.bed')
    fout= open(inputBed, 'w')
    for line in sys.stdin:
        fout.write(line)
    fout.close()
else:
    inputBed= args.input

inbed= pybedtools.BedTool(inputBed)

## 1. Get extremes of each chrom
grp= inbed.groupby(g= [1], c= [2,3], ops= ['min', 'max'], stream= False)

## 2. Divide each chrom in windows
windows= grp.window_maker(b= grp.fn, w= args.window_size, s= args.step_size, stream= True)

## 3. Assign bed features to windows
intsct= windows.intersect(b= inbed, wa= True, wb= True, stream= True)

## 4. Summarize windows
summWinds= intsct.groupby(g= [1,2,3], c= 3 + args.scoreColumn, o= args.ops, stream= True)

for line in summWinds:
    print('\t'.join([line.chrom, str(line.start), str(line.end), str(line[3])]))

if args.tmpdir is None:
    shutil.rmtree(tmpdir)

sys.exit()