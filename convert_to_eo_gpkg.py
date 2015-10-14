#!/usr/bin/env python

import sys
import os
import argparse

from utils_geopackage import *

def main(args):

    parser = argparse.ArgumentParser()

    parser.add_argument("input_file", type=str)
    parser.add_argument("output_file", type=str)

    parsed = parser.parse_args(args)

    input_file = parsed.input_file
    output_file = parsed.output_file

    #out_tiles = initialize_spatialite_file(output_file)

    write_tiles_to_gpkg(input_file, output_file)


def write_tiles_to_gpkg(input_file, output_file):
    print input_file, output_file

    herbert = Geopackage(output_file, 4326)

    print help(herbert)

    # if not output_file, create output_file
    # if output_file, if not eo_gpkg schema, initialize_eo_gpkg_schema
    # else:
    # determine highest zoom level
    # tilify highest zoom level
    # write zoom level
    # create pyramids until zoom level 0


def create_eo_gpkg_tiles(output_file):
    # create spatialite file
    # initialize_eo_gpkg_schema
    pass


def initialize_eo_gpkg_schema(output_file):
    out_tiles = None
    # Check if file exists.
    # Create spatialite file if not.

    # Open existing file
    pass



if __name__ == "__main__":
    main(sys.argv[1:])
