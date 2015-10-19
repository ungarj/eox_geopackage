#!/usr/bin/env python

# Parts of this tool were taken from https://github.com/GitHubRGI/geopackage-python

from collections import OrderedDict
from sqlite3 import connect
import os
import io

class EOGeopackage():
    """
    The EOGeopackage class helps to create and modify a EO Geopackage file.
    """

    def __enter__(self):
        return self

    def __init__(
        self,
        file_path,
        data_type,
        projection,
        overwrite=False
        ):
        """
        Initializes geopackage file and creates EOGeopackage object.
        """
        try:
            assert data_type in ("image/TIFF", "xray")
        except:
            raise
        self.file_path = file_path
        self.data_type = data_type
        self.projection = projection
        self.overwrite = overwrite
        self.projection, self.overwrite
        self.db_connection = connect(self.file_path)
        self.__create_file(overwrite=overwrite)


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
        self.db_connection = connect(self.file_path, detect_types=sqlite3.PARSE_DECLTYPES)
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
                    ("epsg", "WGS 84", ref_sys_wkt[self.projection])
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
                    str(self.projection)
                    )
                )
            except:
                raise
                pass


    def insert_tile(self, zoom, row, col, data):
        if self.data_type == "xray":
            print "hui"
        with self.db_connection as db_connection:
            cursor = db_connection.cursor()
            cursor.execute("""
                INSERT INTO tiles
                    (zoom_level, tile_row, tile_column, tile_data)
                    VALUES (?,?,?,?)
            """, (zoom, row, col, data))


    def get_tiledata(self, zoom, row, col):
        with self.db_connection as db_connection:
            cursor = db_connection.cursor()
            cursor.execute("""
                SELECT tile_data from tiles WHERE
                zoom_level=? AND tile_row=? AND tile_column=?;
            """, (str(zoom), str(row), str(col)))
            return cursor.fetchone()[0]

    def __exit__(self, type, value, traceback):
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
import sqlite3
import numpy as np
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
    """),
    ("tiles",
    """
    CREATE TABLE IF NOT EXISTS tiles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      zoom_level INTEGER NOT NULL,
      tile_column INTEGER NOT NULL,
      tile_row INTEGER NOT NULL,
      tile_data ARRAY NOT NULL,
      UNIQUE (zoom_level, tile_column, tile_row)
    );
    """)
    ])
