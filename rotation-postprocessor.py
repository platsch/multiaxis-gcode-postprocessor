#!/usr/bin/env python

import sys, getopt
import os
import re
import math

def analyze(file, extruder_l, rotatex = False, rotatey = False, dry = False):
    # file handles
    ifh = open(file, 'r')
    (root, ext) = os.path.splitext(file)
    ofh = open(root+'_rotating-axis'+ext, 'w')

 
    # iterate over gcode file line by line
    lastline = ""
    lastx = None
    lasty = None
    lastz = None
    last_angle_y = 0.0
    while True:
        line = ifh.readline()
        newline = ""
        
        extrusion = re.match('G1 X(\d+.\d+) Y(\d+.\d+) Z(\d+.\d+) E(\d+.\d+)(.*)', line)
        if extrusion is not None:
            x = float(extrusion.group(1))
            y = float(extrusion.group(2))
            z = float(extrusion.group(3))
            e = float(extrusion.group(4))
            rest = str(extrusion.group(5))

            newx = x
            newy = y
            newz = z

            anglex = 0.0
            angley = 0.0

            # we have an extrusion and the last position is known
            if(lastx and lasty and lastz):

                # X-axis rotation
                if(rotatex):
                    # compute angle
                    length = x - lastx
                    z_diff = z - lastz
                    if(length > 0):
                        anglex = math.atan(z_diff/length)

                    newy = y + extruder_l*math.sin(anglex)
                    newz = z - (extruder_l - extruder_l*math.cos(anglex))

                # Y-axis rotation
                if(rotatey):
                    # compute angle
                    length = y - lasty
                    z_diff = z - lastz
                    if(length > 0):
                        angley = math.atan(z_diff/length)

                    #print("angley: " + str(math.degrees(angley)))
                    newx = x + extruder_l*math.sin(angley)
                    newz = z - (extruder_l - extruder_l*math.cos(angley))

            newline += 'G1 X' + "{:.4f}".format(newx) + ' Y' + "{:.4f}".format(newy) + ' Z' + "{:.4f}".format(newz) + ' U' + "{:.4f}".format(math.degrees(angley + anglex)) + 'E' + "{:.4f}".format(e) + rest + '\n'


        else:
            newline = line




        # log last position
        pos = re.match('G1 X(\d+.\d+) Y(\d+.\d+)', line)
        if pos is not None:
            lastx = float(pos.group(1))
            lasty = float(pos.group(2))
        pos = re.match('G1 .* Z(\d+.\d+)', line)
        if pos is not None:
            lastz = float(pos.group(1))

        if(dry):
            l = re.match('(G1.*)(E\d+.\d+)(.*)', newline)
            if l is not None:
                #x = float(extrusion.group(1))
                newline = l.group(1) + l.group(3) + '\n'

        ofh.write(newline)

        if not line:
            break

def usage():
    print('Usage:')
    print('')
    print('Either -x or -x or must be provided. If no axis is provided, -y is assumed as default.')
    print('  -x \t\t enable X-axis rotation')
    print('  -y \t\t enable Y-axis rotation')
    print('  -l <length> \t set length of rotating tool (in mm) measured from center of rotation to tooltip')
    print('  -d \t\t dry run, supress output of E-codes')

if __name__ == "__main__":
    if(len(sys.argv) < 2):
        usage()
    else:
        rotatex = False
        rotatey = False
        extruder_l = 30
        dry = False
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
            opts, args = getopt.getopt(sys.argv[2:],"hxyl:d")
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
            elif opt in ("-d"):
                print("Warning: exporting dry code!")
                dry = True

        if(rotatex and rotatey):
            print("Rotating both axis is currently not supported. This will probably change in the near future!")
            usage()
            sys.exit(2)
        if(not rotatex and not rotatey):
            print("No rotation-axis specified, fallback to y as default!")
            rotatey = True

        analyze(in_file, extruder_l, rotatex = rotatex, rotatey = rotatey, dry = dry)