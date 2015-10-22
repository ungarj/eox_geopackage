#!/usr/bin/env python

import sys
import os
import argparse
import numpy as np
from sqlite3 import Binary as sbinary
from datetime import datetime
import zlib

from utils_geopackage import *

def main(args):

    output_file = "test.gpkgx"

    try:
        run_tests(output_file)
    except:
        raise
    finally:
        os.remove(output_file)
        pass

def run_tests(output_file):


    # Test if file is created.
    first_geopackage = EOGeopackage(output_file, "xray", 4326)
    try:
        assert os.path.isfile(output_file)
        first_creation_time = os.path.getctime(output_file)
        print "file creation OK"
    except:
        raise
    try:
        assert schema_is_ok(first_geopackage)
        print "schema OK"
    except:
        raise

    # Test if file is overwritten.
    second_geopackage = EOGeopackage(
        output_file,
        "image/TIFF",
        4326,
        overwrite=True
        )
    try:
        assert os.path.isfile(output_file)
        second_creation_time = os.path.getctime(output_file)
    except:
        raise
    try:
        assert second_creation_time > first_creation_time
        print "file overwrite OK"
    except:
        raise
    try:
        assert schema_is_ok(second_geopackage)
        print "schema OK"
    except:
        raise

    # Test if file is updated (creation time must stay the same).
    updated_geopackage = EOGeopackage(output_file, "xray", 4326)
    try:
        assert os.path.isfile(output_file)
        updated_creation_time = os.path.getctime(output_file)
    except:
        raise
    try:
        assert second_creation_time == updated_creation_time
        print "file update OK"
    except:
        raise
    try:
        assert schema_is_ok(updated_geopackage)
        print "schema OK"
    except:
        raise

    # Performance test.
    zoom = 10
    tilesize = 10

    # Uncompressed data.
    # =================
    print "inserting %s uncompresseed tiles..." %(tilesize*tilesize)
    test_geopackage = EOGeopackage(output_file, "xray", 4326, overwrite=True, compression=None)
    start = datetime.now()
    for row in range(0, tilesize):
        for col in range(0, tilesize):
            test_data = np.random.randint(255, size=(255, 255))
            test_geopackage.insert_tile(zoom, row, col, test_data)
    finish = datetime.now()
    tdelta = finish - start
    seconds = tdelta.total_seconds()

    # Get file size.
    filestat = os.stat(output_file)
    filesize = filestat.st_size
    filesize_mb = filesize/1024
    print "uncompressed filesize: %s KB (%s seconds)" %(filesize_mb, seconds)

    # Test read data.
    test_data = np.random.rand(255, 255)
    zoom, row, col = (3, 5, 7)
    try:
        test_geopackage.insert_tile(zoom, row, col, test_data)
        pass
    except:
        raise
    try:
        test_read = test_geopackage.get_tiledata(zoom, row, col)
        assert isinstance(test_read, np.ndarray)
        assert test_read.all() == test_data.all()
    except:
        raise


    # Comressed data.
    # ===============
    for compression in (
        "blosclz",
        "lz4",
        "lz4hc",
        "snappy",
        "zlib"#
        ):
        print "inserting %s %s compressed tiles..." %(tilesize*tilesize, compression)
        test_geopackage = EOGeopackage(
            output_file,
            "xray",
            4326,
            overwrite=True,
            compression=compression
            )
        start = datetime.now()
        zoom = 10
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = np.random.randint(255, size=(255, 255))
                test_geopackage.insert_tile(zoom, row, col, test_data)
        finish = datetime.now()
        tdelta = finish - start
        seconds = tdelta.total_seconds()

        # Get file size.
        filestat = os.stat(output_file)
        filesize = filestat.st_size
        filesize_mb = filesize/1024
        print "%s compressed filesize: %s KB (%s seconds)" %(
            compression,
            filesize_mb,
            seconds)

        # Test read data.
        test_data = np.random.rand(255, 255)
        zoom, row, col = (3, 5, 7)
        try:
            test_geopackage.insert_tile(zoom, row, col, test_data)
            pass
        except:
            raise
        try:
            test_read = test_geopackage.get_tiledata(zoom, row, col)
            assert isinstance(test_read, np.ndarray)
            assert test_read.all() == test_data.all()
        except:
            print type(test_read)
            raise


def schema_is_ok(geopackage):
    """
    Checks if all necessary tables exist.
    """
    with geopackage.db_connection as db_connection:
        cursor = db_connection.cursor()
        for table in sql_create_tables:
            cursor.execute("""
                SELECT name FROM sqlite_master WHERE type='table' AND name='%s'
                """ %(table)
            )
            if cursor.fetchone():
                pass
            else:
                return table
    return True


if __name__ == "__main__":
    main(sys.argv[1:])
