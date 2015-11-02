#!/usr/bin/env python

# Parts of this tool were taken from https://github.com/GitHubRGI/geopackage-python

from collections import OrderedDict
from sqlite3 import connect
import sqlite3
import numpy as np
import os
import io
import blosc
from sqlite3 import Binary
from PIL import Image
try:
    from cStringIO import StringIO as ioBuffer
except ImportError:
    from io import BytesIO as ioBuffer

class EOGeopackage():
    """
    The EOGeopackage class helps to create and modify a EO Geopackage file.
    Parameters:
    - file_path: path to .gpkgx file to be created or modified
    - data_type: either "image/TIFF" for standard 2D images or "xray" for
      multidimensional arrays
    - srs: please use 4326 (WGS84 Geographic Projection), support for 3857
      (Google Spherical Mercator) will be added.
    - overwrite: either False (just insert tiles which don't yet exist) or True
      (delete source file first).
    - compression: compression used.
      - image/TIFF supported compressions:
        - tiff_ccitt
        - group3
        - group4
        - tiff_jpeg
        - tiff_adobe_deflate
        - tiff_thunderscan
        - tiff_deflate
        - tiff_sgilog
        - tiff_sgilog24
        - tiff_raw_16
      - xray supported compressions (default=lz4):
        - blosclz
        - lz4
        - lz4hc
        - snappy
        - zlib
    """


    def __enter__(self):
        return self


    def __init__(
        self,
        file_path,
        mode=None,
        data_type=None,
        srs=None,
        overwrite=False,
        compression=None
        ):
        """
        Initializes geopackage file and creates EOGeopackage object.
        """
        self.file_path = file_path
        try:
            assert mode
        except:
            raise AttributeError("please provide mode (r or w)")
        if mode == 'w':
            try:
                assert data_type
            except:
                raise AttributeError("data_type not provided")
            try:
                assert srs
            except:
                assert AttributeError("srs not provided")
            self.data_type = data_type
            self.srs = srs
        elif mode == 'r':
            # Assert that file exists.
            try:
                assert os.path.isfile(self.file_path)
            except:
                raise IOError("file '%s' not found" % self.file_path)
            # Assert that file has the correct schema.
            try:
                self.db_connection = connect(self.file_path)
                assert schema_is_ok(self.file_path)
            except:
                raise IOError("not a valid EO Geopackage file")
            # Read metadata.
            self.data_type = self.__get_data_type()
            self.srs = self.__get_srs()
        else:
            raise AttributeError("unknown mode %s" % mode)
        # Assert that data_type is given.
        try:
            assert self.data_type
        except:
            raise AttributeError("no data_type provided")
        # Assert that data_type is valid.
        try:
            assert self.data_type in ("image/TIFF", "xray")
        except:
            raise AttributeError("unknown data_type %s" % self.data_type)
        # Assert that SRS is given.
        try:
            assert self.srs
        except:
            raise AttributeError("no SRS provided")
        # Assert that SRS is valid.
        try:
            assert self.srs in ([4326])
        except:
            raise AttributeError("unknown SRS %s" % str(self.srs))
        self.compression = compression
        if self.data_type == "xray":
            if compression:
                try:
                    assert compression in (
                        "blosclz",
                        "lz4",
                        "lz4hc",
                        "snappy",
                        "zlib"
                        )
                except:
                    raise AttributeError("Unknown compression %s" % compression)
            else:
                compression="lz4"
        if self.data_type == "image/TIFF":
            if compression:
                try:
                    assert compression in (
                        "tiff_ccitt",
                        "group3",
                        "group4",
                        "tiff_jpeg",
                        "tiff_adobe_deflate",
                        "tiff_thunderscan",
                        "tiff_deflate",
                        "tiff_sgilog",
                        "tiff_sgilog24",
                        "tiff_raw_16"
                        )
                except:
                    raise AttributeError("Unknown compression %s" % compression)
            else:
                compression=None
        self.overwrite = overwrite
        self.db_connection = connect(self.file_path)
        if mode != "r":
            self.__create_file(overwrite=overwrite)



    def __get_data_type(self):
        db_connection = connect(self.file_path)
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT identifier from gpkg_contents;
            """)
        data_type = cursor.fetchone()[0].split(' ')[0]
        return data_type

    def __get_srs(self):
        db_connection = connect(self.file_path)
        cursor = db_connection.cursor()
        cursor.execute("""
            SELECT srs_id from gpkg_contents;
            """)
        srs_id = cursor.fetchone()[0]
        return srs_id


    def __create_file(self, overwrite=False):
        """
        Creates a new geopackage file (i.e. including schema).
        """
        try:
            assert os.path.isfile(self.file_path)
        except:
            raise IOError
        if overwrite:
            os.remove(self.file_path)
        self.db_connection = connect(
            self.file_path,
            detect_types=sqlite3.PARSE_DECLTYPES
            )
        self.__create_schema()


    def __create_schema(self):
        with self.db_connection as db_connection:
            cursor = db_connection.cursor()

            # Basic schema.
            try:
                for table, statement in sql_create_tables.iteritems():
                    cursor.execute(statement)
            except:
                raise

            # Spatial reference.
            try:
                cursor.execute("""
                    INSERT INTO gpkg_spatial_ref_sys (
                        srs_id,
                        organization,
                        organization_coordsys_id,
                        srs_name,
                        definition)
                    VALUES (4326, ?, 4326, ?, ?)
                    """,
                    ("epsg", "WGS 84", ref_sys_wkt[self.srs])
                )
            except:
                print "Warning: EPSG definition already exists"

            # Dataset description.
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO gpkg_contents (
                        table_name,
                        data_type,
                        identifier,
                        description,
                        min_x,
                        max_x,
                        min_y,
                        max_y,
                        srs_id)
                    VALUES (?, ?, ?, ?, 0, 0, 0, 0, ?);
                    """,
                    (
                    "tiles",
                    "tiles",
                    (self.data_type + " Raster Tiles"),
                    content_description,
                    str(self.srs)
                    )
                )
            except:
                raise


            # Tiles table.

            if self.data_type == "xray":
                tiles_data_type = "ARRAY"
                if self.compression:
                    tiles_data_type = "TEXT"
            elif self.data_type in ("image/TIFF", "image/JPEG2000"):
                tiles_data_type = "BLOB"
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS tiles (
                      id INTEGER PRIMARY KEY AUTOINCREMENT,
                      zoom_level INTEGER NOT NULL,
                      tile_column INTEGER NOT NULL,
                      tile_row INTEGER NOT NULL,
                      tile_data %s NOT NULL,
                      UNIQUE (zoom_level, tile_column, tile_row)
                    );
                    """ %(tiles_data_type)
                )
            except:
                raise


    def insert_tile(self, zoom, row, col, data):
        with self.db_connection as db_connection:
            cursor = db_connection.cursor()
            compression = self.compression
            data_type = self.data_type
            if compression and (data_type == "xray"):
                db_connection.text_factory = str
                data_compressed = blosc.pack_array(data, cname=compression)
                data = data_compressed
            if data_type == "image/TIFF":
                try:
                    assert data.dtype == "uint8"
                except:
                    raise TypeError("dtype %s not supported" % data.dtype)
                image = Image.fromarray(np.uint8(data))
                buf = ioBuffer()
                image.save(buf, "tiff")
                buf.seek(0)
                data = Binary(buf.read())
            if data_type == "image/JPEG2000":
                try:
                    assert data.dtype == "uint8"
                except:
                    raise TypeError("dtype %s not supported" % data.dtype)
                image = Image.fromarray(np.uint8(data))
                buf = ioBuffer()
                image.save(buf, "j2k")
                buf.seek(0)
                data = Binary(buf.read())
            try:
                cursor.execute("""
                    INSERT INTO tiles
                        (zoom_level, tile_row, tile_column, tile_data)
                        VALUES (?,?,?,?)
                """, (zoom, row, col, data))
            except:
                raise


    def get_tiledata(self, zoom, row, col):
        with self.db_connection as db_connection:
            cursor = db_connection.cursor()
            data_type = self.data_type
            if self.compression and (data_type == "xray"):
                db_connection.text_factory = str
            try:
                cursor.execute("""
                    SELECT tile_data from tiles WHERE
                    zoom_level=? AND tile_row=? AND tile_column=?;
                """, (str(zoom), str(row), str(col)))
            except:
                raise
            if self.compression and (data_type == "xray"):
                data = blosc.unpack_array(cursor.fetchone()[0])
            else:
                data = cursor.fetchone()[0]
            if data_type == "image/TIFF":
                # img = Image.frombuffer("L", (255, 255), data)
                img = Image.open(ioBuffer(data))
                print img.format, img.mode
                data = np.array(img)
            return data


    def __exit__(self):
        """Resource cleanup on destruction."""
        self.db_connection.close()


# From http://stackoverflow.com/questions/18621513/python-insert-numpy-array-into-sqlite3-database
def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597 (SoulNibbler)
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())
def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)
# Converts np.array to TEXT when inserting
sqlite3.register_adapter(np.ndarray, adapt_array)
# Converts TEXT to np.array when selecting
sqlite3.register_converter("array", convert_array)

content_description = """
Experimental EO GPKG raster tiles by EOX IT Services (ju@eox.at)
"""

ref_sys_wkt = {
    4326: """
    GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,
    298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG",
    "6326"]],PRIMEM["Greenwich",0,AUTHORITY["EPSG","8901"]],UNIT
    ["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],
    AUTHORITY["EPSG","4326"]]
    """
    }


sql_create_tables = OrderedDict([
    ("gpkg_spatial_ref_sys",
    """
    CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
      srs_name TEXT NOT NULL,
      srs_id INTEGER NOT NULL PRIMARY KEY,
      organization TEXT NOT NULL,
      organization_coordsys_id INTEGER NOT NULL,
      definition  TEXT NOT NULL,
      description TEXT
    );
    """
    ),
    ("gpkg_contents",
    """
    CREATE TABLE IF NOT EXISTS gpkg_contents (
      table_name TEXT NOT NULL PRIMARY KEY,
      data_type TEXT NOT NULL,
      identifier TEXT UNIQUE,
      description TEXT DEFAULT '',
      last_change DATETIME NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
      min_x DOUBLE,
      min_y DOUBLE,
      max_x DOUBLE,
      max_y DOUBLE,
      srs_id INTEGER,
      CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES
        gpkg_spatial_ref_sys(srs_id)
    );
    """),
    ("gpkg_geometry_columns",
    """
    CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
      table_name TEXT NOT NULL,
      column_name TEXT NOT NULL,
      geometry_type_name TEXT NOT NULL,
      srs_id INTEGER NOT NULL,
      z TINYINT NOT NULL,
      m TINYINT NOT NULL,
      CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
      CONSTRAINT uk_gc_table_name UNIQUE (table_name),
      CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES
        gpkg_contents(table_name),
      CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys
        (srs_id)
    );
    """),
    ("gpkg_tile_matrix_set",
    """
    CREATE TABLE IF NOT EXISTS gpkg_tile_matrix_set (
      table_name TEXT NOT NULL PRIMARY KEY,
      srs_id INTEGER NOT NULL,
      min_x DOUBLE NOT NULL,
      min_y DOUBLE NOT NULL,
      max_x DOUBLE NOT NULL,
      max_y DOUBLE NOT NULL,
      CONSTRAINT fk_gtms_table_name FOREIGN KEY (table_name) REFERENCES
        gpkg_contents(table_name),
      CONSTRAINT fk_gtms_srs FOREIGN KEY (srs_id) REFERENCES
        gpkg_spatial_ref_sys (srs_id)
    );
    """),
    ("gpkg_tile_matrix",
    """
    CREATE TABLE IF NOT EXISTS gpkg_tile_matrix (
      table_name TEXT NOT NULL,
      zoom_level INTEGER NOT NULL,
      matrix_width INTEGER NOT NULL,
      matrix_height INTEGER NOT NULL,
      tile_width INTEGER NOT NULL,
      tile_height INTEGER NOT NULL,
      pixel_x_size DOUBLE NOT NULL,
      pixel_y_size DOUBLE NOT NULL,
      CONSTRAINT pk_ttm PRIMARY KEY (table_name, zoom_level),
      CONSTRAINT fk_tmm_table_name FOREIGN KEY (table_name) REFERENCES
        gpkg_contents(table_name)
    );
    """)
    ])


def schema_is_ok(geopackage_path):
    """
    Checks if all necessary tables exist.
    """
    with connect(geopackage_path) as db_connection:
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
