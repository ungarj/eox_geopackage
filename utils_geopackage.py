#!/usr/bin/env python

import collections

class EOGeopackage():
    """
    The EOGeopackage class helps to create and modify a EO Geopackage file.
    """

    def __enter__(self):
        return self

    def __init__(
        filename,
        directory,
        data_type,
        overwrite=False,
        update=True
        ):
        try:
            assert data_type in ("image/TIFF", "xray")
        except:
            raise
        self.name = filename
        self.path = os.path.join(directory, filename)
        self.__db_connection = connect(self.path)
        self.data_type = data_type
        self.overwrite = overwrite
        __create_file(overwrite)

    def __create_file(overwrite=False, update=False):
        if not os.path.isfile:
            # Create new file if it doesn't exist yet.
            pass
            # create file
            # create schema
        elif overwrite:
            # If file exists but shall be overwritten, delete file and create
            # new one.
            os.remove(self.path)
            __create_file(self.path)
        else:
            # If file exists, check whether it holds the correct schema. Create
            # schema if necessary and proceed.
            # check if schema exists
            # create schema
            __create_schema(self.path)

    def __create_schema(self.__db_connection):
        with self.__db_connection as db_connection:
            cursor = db_connection.cursor()
            # Create tables.
            for table, statement in sql_create_tables.iteritems():
                cursor.execute(statement)
            # Create triggers.
            for trigger, statement in sql_create_triggers.iteritems():
                cursor.execute(statement)

sql_create_tables = {
    "gpkg_spatial_ref_sys":
    """
    CREATE TABLE gpkg_spatial_ref_sys (
      srs_name TEXT NOT NULL,
      srs_id INTEGER NOT NULL PRIMARY KEY,
      organization TEXT NOT NULL,
      organization_coordsys_id INTEGER NOT NULL,
      definition  TEXT NOT NULL,
      description TEXT
    """,
    "gpkg_contents":
    """
    CREATE TABLE gpkg_contents (
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
    """,
    "gpkg_geometry_columns":
    """
    CREATE TABLE gpkg_geometry_columns (
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
    """,
    "gpkg_tile_matrix_set":
    """
    CREATE TABLE gpkg_tile_matrix_set (
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
    """,
    "gpkg_tile_matrix":
    """
    CREATE TABLE gpkg_tile_matrix (
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
    """
    }.OrderedDict()

sql_create_triggers = """
    CREATE TRIGGER 'gpkg_tile_matrix_zoom_level_insert'
    BEFORE INSERT ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates
      constraint: zoom_level cannot be less than 0')
    WHERE (NEW.zoom_level < 0);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_zoom_level_update'
    BEFORE UPDATE of zoom_level ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates
      constraint: zoom_level cannot be less than 0')
    WHERE (NEW.zoom_level < 0);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_matrix_width_insert'
    BEFORE INSERT ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates
      constraint: matrix_width cannot be less than 1')
    WHERE (NEW.matrix_width < 1);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_matrix_width_update'
    BEFORE UPDATE OF matrix_width ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates
      constraint: matrix_width cannot be less than 1')
    WHERE (NEW.matrix_width < 1);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_matrix_height_insert'
    BEFORE INSERT ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates
      constraint: matrix_height cannot be less than 1')
    WHERE (NEW.matrix_height < 1);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_matrix_height_update'
    BEFORE UPDATE OF matrix_height ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates
      constraint: matrix_height cannot be less than 1')
    WHERE (NEW.matrix_height < 1);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_pixel_x_size_insert'
    BEFORE INSERT ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates
      constraint: pixel_x_size must be greater than 0')
    WHERE NOT (NEW.pixel_x_size > 0);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_pixel_x_size_update'
    BEFORE UPDATE OF pixel_x_size ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates
      constraint: pixel_x_size must be greater than 0')
    WHERE NOT (NEW.pixel_x_size > 0);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_pixel_y_size_insert'
    BEFORE INSERT ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates
      constraint: pixel_y_size must be greater than 0')
    WHERE NOT (NEW.pixel_y_size > 0);
    END

    CREATE TRIGGER 'gpkg_tile_matrix_pixel_y_size_update'
    BEFORE UPDATE OF pixel_y_size ON 'gpkg_tile_matrix'
    FOR EACH ROW BEGIN
    SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates
      constraint: pixel_y_size must be greater than 0')
    WHERE NOT (NEW.pixel_y_size > 0);
    END
    """
    # insert
    # update
    # .name
    # .path
    # get_tile(zoom, row, col)
    # get_tile_as_array(zoom, row, col)

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
