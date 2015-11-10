#!/usr/bin/env python

import sys
import os
import argparse
import rasterio

from utils_geopackage import *

# import local modules independent from script location
rootdir = os.path.dirname(os.path.realpath(__file__))
submodules_folder = os.path.join(rootdir, 'submodules')
tilematrix_module_directory = os.path.join(submodules_folder, 'tilematrix')
tilematrix_class_directory = os.path.join(tilematrix_module_directory, 'src')
sys.path.append(tilematrix_class_directory)

from tilematrix import *
from tilematrix_io import *

def main(args):
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", type=str)
    parser.add_argument("output_gpkg", type=str)
    parsed = parser.parse_args(args)
    input_file = parsed.input_file
    output_gpkg = parsed.output_gpkg

    try:
        save_tiff(input_file, output_gpkg)
    except:
        if os.path.isfile(output_gpkg):
            os.remove(output_gpkg)
        raise


def save_tiff(input_file, output_gpkg):
    zoom = 3
    tiff_gpkg = EOGeopackage(
        output_gpkg,
        "w",
        "image/TIFF",
        4326,
        overwrite=True,
        compression=None
        )
    wgs84 = TileMatrix("4326")
    wgs84.set_format("GTiff")

    with rasterio.open(input_file, "r") as src:
        bounds = src.bounds
        tl = [bounds[0], bounds[3]]
        tr = [bounds[2], bounds[3]]
        br = [bounds[2], bounds[1]]
        bl = [bounds[0], bounds[1]]
        bbox = Polygon([tl, tr, br, bl])
        tiles = wgs84.tiles_from_bbox(bbox, zoom)
        for tile in tiles:
            metadata, rasterdata = read_raster_window(
                input_file,
                wgs84,
                tile,
                pixelbuffer=2
            )
            zoom, row, col = tile
            tiff_gpkg.insert_tile(zoom, row, col, rasterdata)


if __name__ == "__main__":
    main(sys.argv[1:])
