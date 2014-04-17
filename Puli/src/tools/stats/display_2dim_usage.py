# -*- coding: utf8 -*-

"""
"""
__author__      = "Jérôme Samson"
__copyright__   = "Copyright 2014, Mikros Image"

import os
import sys
import csv
import time
import datetime
from optparse import OptionParser

import numpy as np
import pygal
from pygal.style import *

try:
    import simplejson as json
except ImportError:
    import json


from octopus.dispatcher import settings
from octopus.core import singletonconfig
from tools.common import roundTime
from tools.common import lowerQuartile, higherQuartile

###########################################################################################################################
# Data example:
# {
#     "prod":{
#           "ddd" :     { "jobs":15, "err":1, "paused":2, "ready/blocked":10, "running":2, "allocatedRN":5, "readyCommandCount":15},
#           "dior_tea" :    { "jobs":1, "err":0, "paused":0, "ready/blocked":0, "running":1, "allocatedRN":1, "readyCommandCount":15},
#     }, 
#     "user":{
#           "brr" :     { "jobs":15, "err":1, "paused":2, "ready/blocked":10, "running":2 , "allocatedRN":5, "readyCommandCount":15},
#           "bho" :     { "jobs":1, "err":0, "paused":0, "ready/blocked":0, "running":1 , "allocatedRN":1, "readyCommandCount":15},
#           "lap" :     { "jobs":1, "err":0, "paused":0, "ready/blocked":0, "running":1 , "allocatedRN":1, "readyCommandCount":15}, 
#     }, 
#     "step":{
#     ...
#     }, 
#     "type":{
#     ...
#     }, 
#     "total": { "jobs":15, "err":1, "paused":2, "ready/blocked":10, "running":2 , "allocatedRN":5, "readyCommandCount":150}
#     "requestDate": "Wed Apr  2 12:16:01 2014"
# }



def process_args():
    '''
    Manages arguments parsing definition and help information
    '''

    usage = "usage: %prog [general options] [restriction list] [output option]"
    desc="""Displays information.
"""

    parser = OptionParser(usage=usage, description=desc, version="%prog 0.1" )

    parser.add_option( "-f", action="store", dest="sourceFile", default=os.path.join(settings.LOGDIR, "usage_stats.log"), help="Source file" )
    parser.add_option( "-o", action="store", dest="outputFile", default="./queue_avg.svg", help="Target output file." )
    parser.add_option( "-v", action="store_true", dest="verbose", help="Verbose output" )
    parser.add_option( "-s", action="store", dest="rangeIn", type="int", help="Start range is N hours in past", default=3 )
    parser.add_option( "-e", action="store", dest="rangeOut", type="int", help="End range is N hours in past (mus be lower than '-s option'", default=0 )
    parser.add_option( "-t", "--title", action="store", dest="title", help="Indicates a title", default="Queue usage over time")
    parser.add_option( "-r", "--res", action="store", dest="resolution", type="int", help="Indicates ", default=10 )
    parser.add_option( "--stack", action="store_true", dest="stacked", default=False)
    parser.add_option( "--line", action="store_true", dest="line", default=True)
    parser.add_option( "--log", action="store_true", dest="logarithmic", help="Display graph with a logarithmic scale", default=False )
    parser.add_option( "--scale", action="store", dest="scaleEvery", type="int", help="Indicates the number of scale values to display", default=8 )

    options, args = parser.parse_args()

    return options, args


if __name__ == "__main__":


    options, args = process_args()
    VERBOSE = options.verbose
    
    if VERBOSE:
        print "Command options: %s" % options
        print "Command arguments: %s" % args

    if len(args) is not 2:
        print "Error: 2 fields must be specified."
        sys.exit(1)
    else:
        groupField = args[0]
        graphValue = args[1]

    
    if options.rangeIn < options.rangeOut:
        print "Invalid start/end range"
        sys.exit()

    startDate = time.time() - 3600 * options.rangeIn
    endDate = time.time() - 3600 * options.rangeOut

    if VERBOSE:
        print "Loading stats: %r " % options.sourceFile
        print "  - from: %r " % datetime.date.fromtimestamp(startDate)
        print "  - to:   %r " % datetime.date.fromtimestamp(endDate)
        print "Start."


    strScale=[]
    scale=[]
    data2Dim = {}
    log = []

    #
    # Load json log and filter by date
    #
    with open(options.sourceFile, "r" ) as f:
        for line in f:
            data = json.loads(line)
            if (startDate < data['requestDate']  and data['requestDate'] <= endDate):
                log.append( json.loads(line) )


    for i, data in enumerate(log):
        eventDate = datetime.datetime.fromtimestamp( data['requestDate'] )

        for key, val in data[ groupField ].items():
            if key not in data2Dim:
                data2Dim[key] = np.array( [0]*len(log) )
            data2Dim[key][i] = val[ graphValue ]

        scale.append( eventDate )


    stepSize = len(scale) / options.resolution
    newshape = (options.resolution, stepSize)
    useableSize = len(scale) - ( len(scale) % options.resolution )

    avgData = {}

    if VERBOSE:
        print "stepSize=%d" % stepSize
        print "useableSize=%d" % useableSize

    for dataset in data2Dim.keys():
        # print "%s = %d - %r" % (dataset, len(data2Dim[dataset]), data2Dim[dataset])
        avgData[dataset] = np.mean( np.reshape(data2Dim[dataset][-useableSize:], newshape), axis=1)

    # working = np.array(nb_working[-useableSize:])
    # unknown = np.array(nb_unknown[-useableSize:])
    # paused = np.array(nb_paused[-useableSize:])


    # # print ("working %d = %r" % (len(working), working) )
    # # print ("reshape %d = %r" % (len(newshape), newshape) )

    # avg_working= np.mean( np.reshape(working, newshape), axis=1)
    # avg_paused= np.mean( np.reshape(paused, newshape), axis=1)
    # avg_unknown= np.mean( np.reshape(unknown, newshape), axis=1)


    # # med= np.median(data, axis=1)
    # # amin= np.min(data, axis=1)
    # # amax= np.max(data, axis=1)
    # # q1= lowerQuartile(data)
    # # q2= higherQuartile(data)
    # # std= np.std(data, axis=1)

    strScale = [''] * options.resolution
    tmpscale = np.reshape(scale[-useableSize:], newshape)
    # # print ("tmp scale %d = %r" % (len(tmpscale), tmpscale) )
    # # print ("str scale %d = %r" % (len(strScale), strScale) )

    for i,date in enumerate(tmpscale[::len(tmpscale)/options.scaleEvery]):
        newIndex = i*len(tmpscale)/options.scaleEvery

        if newIndex < len(strScale):
            strScale[newIndex] = date[0].strftime('%H:%M')

    strScale[0] = scale[0].strftime('%Y-%m-%d %H:%M')
    strScale[-1] = scale[-1].strftime('%Y-%m-%d %H:%M')

    if VERBOSE:
        print ("newshape %d = %r" % (len(newshape), newshape) )
        print ("data2Dim %d = %r" % (len(data2Dim), data2Dim) )
        print ("scale %d = %r" % (len(strScale), strScale) )

    if VERBOSE:
        print "Num events: %d" % len(scale)
        print "Creating graph."


    if options.stacked:
        avg_usage = pygal.StackedLine( x_label_rotation=30,
                                include_x_axis=True,
                                logarithmic=options.logarithmic, 
                                show_dots=False,
                                width=800, 
                                height=300,
                                fill=True,
                                interpolate='hermite', 
                                interpolation_parameters={'type': 'cardinal', 'c': 1.0},
                                interpolation_precision=3,
                                style=RedBlueStyle
                                )
    else:
        avg_usage = pygal.Line( x_label_rotation=30,
                                include_x_axis=True,
                                logarithmic=options.logarithmic, 
                                show_dots=True,
                                width=800, 
                                height=300,
                                interpolate='hermite', 
                                interpolation_parameters={'type': 'cardinal', 'c': 1.0},
                                interpolation_precision=3,
                                style=RedBlueStyle
                                )

    avg_usage.title = options.title
    avg_usage.x_labels = strScale

    for key,val in avgData.items():
        avg_usage.add(key, val )

    avg_usage.render_to_file( options.outputFile )

    if VERBOSE:
        print "Done."

