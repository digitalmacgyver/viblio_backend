#!/usr/bin/env python

import commands
import glob
import json
import operator
import os
import re
import shutil
import sys

import vib.rekog.utils as rekog

import vib.config.AppConfig
config = vib.config.AppConfig.AppConfig( 'viblio' ).config()

root_dir = '/wintmp/youtube-test/beautifymeehtv/'
video_input_dirs = glob.glob( '%s*' % ( root_dir ) )

#video_input_dirs = [ '/wintmp/wedding-album/' ]

workdir = '/wintmp/youtube-test/workdir'
outdir = '/wintmp/youtube-test/outdir'

def get_frames( input_filename, output_file, uid, frame_count ):

    cmd = '/usr/local/bin/ffmpeg -y -i %s -vf scale=800x450 %s' % ( input_filename, output_file )

    print "Running:", cmd
    ( status, cmd_output ) = commands.getstatusoutput( cmd )

    cmd_output = cmd_output.decode( 'utf-8' )
    print "Output was:", cmd_output

    input_frames = re.findall( r'frame=\s*(\d+)\s', cmd_output )
    frames = float( input_frames[-1] )
    cmd = '/usr/local/bin/ffmpeg -y -i %s' % ( output_file )

    print "Running:", cmd
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    print "Output was:", cmd_output
                
    fps_string = re.search( r',\s+([\d\.]+)\s+fps', cmd_output )
    
    if fps_string is not None:
        fps = float( fps_string.groups()[0] )
    else:
        raise Exception( 'Could not determine fps to generate animated thumbnail.' )

    input_length = float( frames ) / fps 
    output_fps = float( frame_count ) / input_length

    cmd = '/usr/local/bin/ffmpeg -y -i %s -vf fps=%s -f image2 %s/%s-thumb-%%04d.png' % ( output_file, output_fps, workdir, uid )

    print "Running:", cmd
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    print "Output was:", cmd_output

def get_face_score( filename ):
    face_score = 0
    result = rekog.detect_for_file( filename )
    for face in result['face_detection']:
        face_score += face['confidence']

    print "Face score:", face_score
    return face_score

def get_blur_score( filename ):
    cmd = '/home/viblio/viblio/faces-working/faces/BlurDetector/blurDetector %s' % ( filename )

    print "Running:", cmd
    ( status, cmd_output ) = commands.getstatusoutput( cmd )
    print "Output was:", cmd_output    

    return float( cmd_output )


def get_best_images( images, count ):
    '''Given an array fo images returns the N best images ordered by
    their goodness, up to count total.'''
    
    # Within each group, return the highest face score, and the least
    # blurry not already returned.
    groups = max( count / 2, 1 )
    images_per_group = len( images ) / groups

    scored_images = {}

    for i in range( 0, groups ):
        scored_images[i] = []
        for j in range( 0, images_per_group ):
            idx = images_per_group * i + j
            face_score = get_face_score( images[idx] )
            blur_score = get_blur_score( images[idx] )
            #face_score = 0
            #blur_score = 0
            scored_images[i].append( { 'image': images[idx], 'face_score' : face_score, 'blur_score' : blur_score } )
    
    results = []

    print "There are:", groups, "groups."

    for group in sorted( scored_images.keys() ):
        group_images = sorted( scored_images[group], key=lambda x: x['image'] )
        group_faces = sorted( group_images, key=lambda x: -x['face_score'] )
        group_blurs = sorted( group_images, key=lambda x: x['blur_score'] )
        print "For group:", group
        print "images were:", images
        print "faces were:", group_faces
        print "blurs were:", group_blurs
        
        face_result = group_faces[0]
        blur_result = group_blurs[0]
        for blur_image in group_blurs:
            if blur_image['image'] == face_result['image']:
                continue
            else:
                blur_result = blur_image
                break

        results.append( face_result )
        results.append( blur_result )

    return results

total_frames = 150
output_frames = 120

for video_dir in video_input_dirs:
    if not os.path.isdir( video_dir ):
        continue
    
    i = 1
    videos = glob.glob( "%s/../*.flv" % ( video_dir ) )

    best_images = []

    '''
    for video in videos:
        print "Found: %s" % ( video )
        get_frames( video, "%s/%s.mov" % ( workdir, i ), i, total_frames / len( videos ) )

        images = sorted( glob.glob( "%s/%s-thumb*.png" % ( workdir, i ) ) )
        '''
    if True:
        images = sorted( glob.glob( "%s/*.png" % ( video_dir ) ) )
        best_images += get_best_images( images, output_frames / len( videos ) )

        i += 1

    print "BEST IMAGES", best_images

    best_i = 1
    for image in best_images:
        shutil.copy( image['image'], "%s/%s-%s.png" % ( outdir, os.path.split( video_dir )[-1], best_i ) )
        best_i += 1

sys.exit( 0 )

#indirs = [ '/wintmp/collage/10', '/wintmp/collage/20', '/wintmp/collage/100' ]
indirs = [ '/wintmp/collage/100' ]
#indirs = [ '/wintmp/collage/10' ]
#indirs = [ '/wintmp/collage/20', '/wintmp/collage/100' ]

oot_dir = '/wintmp/youtube-test/beautifymeehtv/'
indirs = glob.glob( '%s*' % ( root_dir ) )

for indir in indirs:
    face_scores = {}
    for filename in glob.glob( "%s/*.png" % ( indir ) ):
        #print "Working on %s" % ( filename )
        face_score = 0
        result = rekog.detect_for_file( filename )
        for face in result['face_detection']:
            face_score += face['confidence']
        face_scores[filename] = face_score
        print "%s %s" % ( filename, face_scores[filename] )

    #face_images = reversed( sorted( face_scores.iteritems(), key=operator.itemgetter( 1 ) ) )

    #for idx, image in enumerate( face_images ):
    #    if idx > 9 or image[1] == 0:
    #        break
    #    shutil.copyfile( image[0], "%s/faces/%s.jpg" % ( indir, idx ) )

