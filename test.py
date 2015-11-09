#!/usr/bin/env python

import sys
import os
import argparse
import numpy as np
from sqlite3 import Binary as sbinary
from datetime import datetime
import zlib

from utils_geopackage import *
import utils_geopackage

def main(args):

    output_file = "test.gpkgx"

    try:
        run_tests(output_file)
    except:
        raise
    finally:
        if os.path.isfile(output_file):
            os.remove(output_file)


def run_tests(output_file):


    # Test if file is created.
    first_geopackage = EOGeopackage(output_file, "w", "xray", 4326)
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
        "w",
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
    updated_geopackage = EOGeopackage(output_file, "r")
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

    # Performance test variables.
    zoom = 10
    tilesize = 10


    ##############
    # image/TIFF #
    ##############

    testarray_size = (255, 255)
    print "TIFF"
    for compression in (
        None,
        # "tiff_ccitt",
        # "group3",
        # "group4",
        # "tiff_jpeg",
        "tiff_adobe_deflate",
        # "tiff_thunderscan",
        "tiff_deflate",
        # "tiff_sgilog",
        # "tiff_sgilog24",
        # "tiff_raw_16",
        "tiff_lzw"
        ):
        # print "inserting %s %s compressed tiles..." %(
        #     tilesize*tilesize,
        #     compression
        #     )
        test_geopackage = EOGeopackage(
            output_file,
            "w",
            "image/TIFF",
            4326,
            overwrite=True,
            compression=compression
            )

        zoom = 10

        # Write data
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = np.uint8(np.random.randint(
                    255,
                    size=testarray_size
                    ))
                test_geopackage.insert_tile(zoom, row, col, test_data)
        finish = datetime.now()
        write_time = (finish - start).total_seconds()

        # Read data.
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = test_geopackage.get_tiledata(zoom, row, col)
        finish = datetime.now()
        read_time = (finish - start).total_seconds()

        # Get file size.
        filestat = os.stat(output_file)
        filesize = filestat.st_size
        filesize_mb = filesize/1024
        print "'%s', %s, %s, %s" %(
            compression,
            filesize_mb,
            write_time,
            read_time)

        # Test read data.
        try:
            test_data = np.uint8(np.random.randint(255, size=testarray_size))
            zoom, row, col = (3, 5, 7)
            test_geopackage.insert_tile(zoom, row, col, test_data)
        except:
            raise
        try:
            test_read = test_geopackage.get_tiledata(zoom, row, col)
            assert isinstance(test_read, np.ndarray)
        except:
            raise
        try:
            np.testing.assert_allclose(test_read, test_data)
        except:
            raise


    ########
    # XRAY #
    ########

    # single band #
    ######
    testarray_size = (255, 255)

    print "numpy single band"
    # Compressed data.
    # ===============
    for compression in (
        None,
        "blosclz",
        "lz4",
        "lz4hc",
        "snappy",
        "zlib"
        ):
        # print "inserting %s %s compressed tiles..." %(
        #     tilesize*tilesize,
        #     compression
        #     )
        test_geopackage = EOGeopackage(
            output_file,
            "w",
            "xray",
            4326,
            overwrite=True,
            compression=compression
            )

        zoom = 10

        # Write data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = np.random.randint(255, size=testarray_size)
                test_geopackage.insert_tile(zoom, row, col, test_data)
        finish = datetime.now()
        write_time = (finish - start).total_seconds()

        # Read data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = test_geopackage.get_tiledata(zoom, row, col)
        finish = datetime.now()
        read_time = (finish - start).total_seconds()

        # Get file size.
        filestat = os.stat(output_file)
        filesize = filestat.st_size
        filesize_mb = filesize/1024
        print "'%s', %s, %s, %s" %(
            compression,
            filesize_mb,
            write_time,
            read_time)

        # Test read data.
        test_data = np.random.randint(255, size=testarray_size)
        zoom, row, col = (3, 5, 7)
        try:
            test_geopackage.insert_tile(zoom, row, col, test_data)
            pass
        except:
            raise
        try:
            test_read = test_geopackage.get_tiledata(zoom, row, col)
            assert isinstance(test_read, np.ndarray)
        except:
            raise
        try:
            np.testing.assert_allclose(test_read, test_data)
        except:
            raise

    # Open geopackage in read mode.
    test_geopackage = None
    test_geopackage = EOGeopackage(output_file, 'r')
    assert test_geopackage.srs == 4326
    assert test_geopackage.data_type == "xray"
    # TODO: test failing!
    # assert isinstance(test_geopackage.get_tiledata(zoom, row, col), np.ndarray)


    # RGB #
    ######
    testarray_size = (255, 255, 3)

    print "numpy RGB"
    # Compressed data.
    # ===============
    for compression in (
        None,
        "blosclz",
        "lz4",
        "lz4hc",
        "snappy",
        "zlib"
        ):
        # print "inserting %s %s compressed 3D tiles..." %(
        #     tilesize*tilesize,
        #     compression
        #     )
        test_geopackage = EOGeopackage(
            output_file,
            "w",
            "xray",
            4326,
            overwrite=True,
            compression=compression
            )

        zoom = 10

        # Write data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = np.random.randint(255, size=testarray_size)
                test_geopackage.insert_tile(zoom, row, col, test_data)
        finish = datetime.now()
        write_time = (finish - start).total_seconds()

        # Read data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = test_geopackage.get_tiledata(zoom, row, col)
        finish = datetime.now()
        read_time = (finish - start).total_seconds()

        # Get file size.
        filestat = os.stat(output_file)
        filesize = filestat.st_size
        filesize_mb = filesize/1024
        print "'%s', %s, %s, %s" %(
            compression,
            filesize_mb,
            write_time,
            read_time)

        # Test read data.
        test_data = np.random.randint(255, size=testarray_size)
        zoom, row, col = (3, 5, 7)
        try:
            test_geopackage.insert_tile(zoom, row, col, test_data)
            pass
        except:
            raise
        try:
            test_read = test_geopackage.get_tiledata(zoom, row, col)
            assert isinstance(test_read, np.ndarray)
        except:
            raise
        try:
            np.testing.assert_allclose(test_read, test_data)
        except:
            raise

    # Open geopackage in read mode.
    test_geopackage = None
    test_geopackage = EOGeopackage(output_file, 'r')
    assert test_geopackage.srs == 4326
    assert test_geopackage.data_type == "xray"
    # TODO: test failing!
    # assert isinstance(test_geopackage.get_tiledata(zoom, row, col), np.ndarray)


    # RGB 3D #
    ######
    testarray_size = (255, 255, 3, 10)

    print "numpy RGB 3D"
    # Compressed data.
    # ===============
    for compression in (
        None,
        "blosclz",
        "lz4",
        "lz4hc",
        "snappy",
        "zlib"
        ):
        # print "inserting %s %s compressed 3D tiles..." %(
        #     tilesize*tilesize,
        #     compression
        #     )
        test_geopackage = EOGeopackage(
            output_file,
            "w",
            "xray",
            4326,
            overwrite=True,
            compression=compression
            )

        zoom = 10

        # Write data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = np.random.randint(255, size=testarray_size)
                test_geopackage.insert_tile(zoom, row, col, test_data)
        finish = datetime.now()
        write_time = (finish - start).total_seconds()

        # Read data.
        start = datetime.now()
        for row in range(0, tilesize):
            for col in range(0, tilesize):
                test_data = test_geopackage.get_tiledata(zoom, row, col)
                tiles = [
                    i
                    for i in test_data
                    ]
        finish = datetime.now()
        read_time = (finish - start).total_seconds()

        # Get file size.
        filestat = os.stat(output_file)
        filesize = filestat.st_size
        filesize_mb = filesize/1024
        print "'%s', %s, %s, %s" %(
            compression,
            filesize_mb,
            write_time,
            read_time)

        # Test read data.
        test_data = np.random.randint(255, size=testarray_size)
        zoom, row, col = (3, 5, 7)
        try:
            test_geopackage.insert_tile(zoom, row, col, test_data)
            pass
        except:
            raise
        try:
            test_read = test_geopackage.get_tiledata(zoom, row, col)
            assert isinstance(test_read, np.ndarray)
        except:
            raise
        try:
            np.testing.assert_allclose(test_read, test_data)
        except:
            raise

    # Open geopackage in read mode.
    test_geopackage = None
    test_geopackage = EOGeopackage(output_file, 'r')
    assert test_geopackage.srs == 4326
    assert test_geopackage.data_type == "xray"
    # TODO: test failing!
    # assert isinstance(test_geopackage.get_tiledata(zoom, row, col), np.ndarray)


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
