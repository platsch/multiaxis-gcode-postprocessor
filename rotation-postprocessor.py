#!/usr/bin/env python

import sys, getopt
import os
import re
import math

from geometry import Point, Line

def analyze(file, extruder_l, rotationlimit, rotatex = False, rotatey = False, dry = False, interpolation = 0):
    # file handles
    ifh = open(file, 'r')
    (root, ext) = os.path.splitext(file)
    ofh = open(root+'_rotating-axis'+ext, 'w')

    rotationlimit = math.radians(rotationlimit)
 
    # iterate over gcode file line by line
    lastline = ""
    lastp = Point()
    modified = False
    lastp_modified = Point()
    laste = 0.0
    last_angle = 0.0
    feedrate = 0.0
    while True:
        line = ifh.readline()
        newlines = []

        f = re.match('.*F(\d+.\d+)', line)
        if f is not None:
            feedrate = float(f.group(1))/60.0 # we use mm/s, not mm/min

        modified = False
        
        extrusion = re.match('G1 X(\d+.\d+) Y(\d+.\d+) Z(\d+.\d+) E(\d+.\d+)(.*)', line)
        if extrusion is not None:
            p = Point(float(extrusion.group(1)), float(extrusion.group(2)), float(extrusion.group(3)))
            e = float(extrusion.group(4))
            rest = str(extrusion.group(5))

            newx = p.x
            newy = p.y
            newz = p.z

            anglex = 0.0
            angley = 0.0

            # we have an extrusion and the last position is known
            if(lastp.is_valid()):

                # X-axis rotation
                if(rotatex):
                    # compute angle
                    length = p.y - lastp.y
                    z_diff = p.z - lastp.z
                    if(abs(length) > 0):
                        anglex = -math.atan(z_diff/length)
                        anglex = max(min(anglex, rotationlimit), -rotationlimit)

                    newy = p.y + extruder_l*math.sin(anglex)
                    newz = p.z - (extruder_l - extruder_l*math.cos(anglex))
                    last_angle = anglex

                    modified = True
                    lastp_modified = Point(p.x, newy, newz)

                    newlines.append('G1 X' + "{:.4f}".format(newx) + ' Y' + "{:.4f}".format(newy) + ' Z' + "{:.4f}".format(newz) + ' U' + "{:.4f}".format(math.degrees(angley + anglex)) + ' E' + "{:.4f}".format(e) + rest + '\n')

                # Y-axis rotation
                if(rotatey):
                    # compute angle
                    length = p.x - lastp.x
                    z_diff = p.z - lastp.z
                    if(abs(length) > 0):
                        angley = -math.atan(z_diff/length)
                        angley = max(min(angley, rotationlimit), -rotationlimit)

                    ipoints = []
                    if(interpolation > 0 and abs(last_angle-angley) > 0.001):
                        ipoints = interpolate(lastp, p, interpolation)
                    else:
                        ipoints.append(p)

                    linetime = lastp.distance_to(p)/feedrate
                    segmenttime = linetime/len(ipoints)

                    for i in range(len(ipoints)):
                        iangle = last_angle + (i+1)*(angley-last_angle)/len(ipoints)
                        ie = last_e + (i+1)*(e-last_e)/len(ipoints)
                        newx = ipoints[i].x + extruder_l*math.sin(iangle)
                        newy = ipoints[i].y
                        newz = ipoints[i].z - (extruder_l - extruder_l*math.cos(iangle))

                        # feedrate
                        seg_feedrate = lastp_modified.distance_to(Point(newx, newy, newz))/segmenttime
                        seg_feedrate = seg_feedrate*60

                        modified = True
                        lastp_modified = Point(newx, newy, newz)

                        if(len(ipoints) > 3):
                            print("i: " + str(i))
                            print("iangle: " + str(iangle) + " (last angle: " + str(last_angle) + " angle: " + str(angley) + ")")
                            print("ie: " + str(ie))
                            print("newx: {:.4f}".format(newx) + " newz: {:.4f}".format(newz))
                            print("feedrate: {:.4f}".format(seg_feedrate))
                        newlines.append('G1 X' + "{:.4f}".format(newx) + ' Y' + "{:.4f}".format(newy) + ' Z' + "{:.4f}".format(newz) + ' U' + "{:.4f}".format(math.degrees(iangle)) + ' E' + "{:.4f}".format(ie) + ' F' + "{:.4f}".format(seg_feedrate) + rest + '\n')

                    last_angle = angley
            else:
                newlines.append('G1 X' + "{:.4f}".format(newx) + ' Y' + "{:.4f}".format(newy) + ' Z' + "{:.4f}".format(newz) + ' U' + "{:.4f}".format(math.degrees(angley + anglex)) + ' E' + "{:.4f}".format(e) + rest + '\n')


        else:
            newlines.append(line)
            last_angle = 0.0




        # log last position
        pos = re.match('G1 X(\d+.\d+) Y(\d+.\d+)', line)
        if pos is not None:
            lastp.x = float(pos.group(1))
            lastp.y = float(pos.group(2))
            if(not modified):
                lastp_modified.x = lastp.x
                lastp_modified.y = lastp.y
        pos = re.match('G1 .* Z(\d+.\d+)', line)
        if pos is not None:
            lastp.z = float(pos.group(1))
            if(not modified):
                lastp_modified.z = lastp.z
        e = re.match('G1.*E(\d+.\d+)', line)
        if e is not None:
            last_e = float(e.group(1))

        for nl in newlines:
            if(dry):
                l = re.match('(G1.*)(E\d+.\d+)(.*)', nl)
                if l is not None:
                    #x = float(extrusion.group(1))
                    nl = l.group(1) + l.group(3) + '\n'

            ofh.write(nl)

        if not line:
            break

def interpolate(a, b, resolution):
    result = []
    length = a.distance_to(b)
    segments = math.ceil(length/resolution)
    l = Line(a, b)
    for i in range(int(segments)):
        result.append(l.point_at((i+1)*(length/segments)))
    return result
    



def usage():
    print('Usage:')
    print('rotation-postprocessor.py [GCode-File] [Options]')
    print('Output will be [GCode-File]_rotating-axis.gcode')
    print('')
    print('Either -x or -x or must be provided. If no axis is provided, -y is assumed as default.')
    print('  -x \t\t\t enable X-axis rotation')
    print('  -y \t\t\t enable Y-axis rotation')
    print('  -l <length> \t\t set length of rotating tool (in mm) measured from center of rotation to tooltip')
    print('  -d --dry \t\t dry run, supress output of E-codes')
    print('  --rotationlimit \t maximum possible angle for tool rotations in degrees. Default: 45.0')
    print('  -i --interpolation \t maximum distance between two adjacent non-horizontal coordinates')

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        usage()
    else:
        rotatex = False
        rotatey = False
        extruder_l = 30.0
        rotationlimit = 45.0
        dry = False
        interpolation = 0
        # Check for valid gcode file
        in_file = sys.argv[1]
        try:
            f = open(in_file)
        except IOError:
            print('Cannot open file ' + str(in_file))
            usage()
            sys.exit(2)
        f.close()

        try:
            opts, args = getopt.getopt(sys.argv[2:],"hxyl:di:",["dry", "rotationlimit=", "interpolation="])
        except getopt.GetoptError as err:
            print(err)
            usage()
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                usage()
                sys.exit()
            elif opt in ("-x"):
                print("rotating X-axis")
                rotatex = True
            elif opt in ("-y"):
                print("rotating Y-axis")
                rotatey = True
            elif opt in ("-l"):
                print("Extruder length is " + str(arg))
                extruder_l = float(arg)
            elif opt in ("-d", "--dry"):
                print("Warning: exporting dry code!")
                dry = True
            elif opt in ("--rotationlimit"):
                rotationlimit = float(arg)
                print("Set rotation limit to {:.4f}deg".format(rotationlimit))
            elif opt in ("-i", "--interpolation"):
                interpolation = float(arg)
                print("Minimum extrusion line length (interpolation) is {:.4f}mm".format(interpolation))

        if(rotatex and rotatey):
            print("Rotating both axis is currently not supported. This will probably change in the near future!\n")
            usage()
            sys.exit(2)
        if(not rotatex and not rotatey):
            print("No rotation-axis specified, fallback to y as default!")
            rotatey = True

        analyze(in_file, extruder_l, rotationlimit, rotatex = rotatex, rotatey = rotatey, dry = dry, interpolation = interpolation)