# experimental gpkg EO tiles

Extended Geopackage (*.gpkgx) storing a tile set pyramid while keeping the original pixel values.

It shall not be limited to 8bit (as in PNG and JPEG) or use lossy compression (JPEG).

## formats

### numpy array
* [insert numpy into sqlite3](http://stackoverflow.com/questions/18621513/python-insert-numpy-array-into-sqlite3-database)
* [xray - labeled arrays](http://xray.readthedocs.org/en/stable/examples/quick-overview.html#indexing)

pros:
- time series storage

cons:
- ~~no compression (i.e. 100 256x256 sized arrays take ca. 50MB disk space); try [blz](http://blz.pydata.org/blz-manual/index.html)~~

#### compression performance

Using random integer numpy arrays and compression options from the [blosc library](http://python-blosc.blosc.org/index.html).

##### 2D: 100 tiles, 256 x 256

| compression   | size (KB) |  time (s) |
| ------------- |----------:| ---------:|
| uncompressed  |    51,035 |     1.815 |
| blosclz       |     6,622 |     0.677 |
| lz4           |     6,622 |     0.632 |
| lz4hc         |     6,622 |     0.903 |
| snappy        |     8,522 |     0.877 |
| zlib          |     6,522 |     1.386 |

##### 3D: 100 tiles, 256 x 256 x 10

| compression   | size (KB) |  time (s) |
| ------------- |----------:| ---------:|
| uncompressed  |   510,035 |    13.674 |
| blosclz       |    65,830 |     4.029 |
| lz4           |    65,672 |     3.603 |
| lz4hc         |    65,622 |    92.097 |
| snappy        |   124,322 |     4.999 |
| zlib          |    64,422 |     9.112 |

TODO: [use bloscpac](http://python-blosc.blosc.org/tutorial.html#packing-numpy-arrays-with-bloscpack)

### TIFF
* [OGC Tiled Elevation Extension (PDF)](https://www.google.at/url?sa=t&rct=j&q=&esrc=s&source=web&cd=4&sqi=2&ved=0CDAQFjADahUKEwiX6aX887zIAhVK7hoKHbfuBts&url=https%3A%2F%2Fportal.opengeospatial.org%2Ffiles%2F%3Fartifact_id%3D63289&usg=AFQjCNHoo85tj0neUFP9jmwBGs9dv6qmpA&sig2=XpINIwbEDLFJ_6Snyk5Ivg&bvm=bv.104819420,d.d2s&cad=rja)

### JPEG2000

## to be researched
* storing metadata masks in tiles as well

## links

* [GPKG in python](https://github.com/GitHubRGI/geopackage-python)

## schema

### tables
* gpkg_spatial_ref_sys
* gpkg_contents
* gpkg_geometry_columns
* gpkg_tile_matrix_set
* gpkg_tile_matrix

### some code

from the [spec](http://www.geopackage.org/spec).

### gpkg_spatial_ref_sys
```sql
CREATE TABLE gpkg_spatial_ref_sys (
  srs_name TEXT NOT NULL,
  srs_id INTEGER NOT NULL PRIMARY KEY,
  organization TEXT NOT NULL,
  organization_coordsys_id INTEGER NOT NULL,
  definition  TEXT NOT NULL,
  description TEXT
);
```

### gpkg_contents
```sql
CREATE TABLE gpkg_contents (
  table_name TEXT NOT NULL PRIMARY KEY,
  data_type TEXT NOT NULL,
  identifier TEXT UNIQUE,
  description TEXT DEFAULT '',
  last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  min_x DOUBLE,
  min_y DOUBLE,
  max_x DOUBLE,
  max_y DOUBLE,
  srs_id INTEGER,
  CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
);
```

### gpkg_geometry_columns
```sql
CREATE TABLE gpkg_geometry_columns (
  table_name TEXT NOT NULL,
  column_name TEXT NOT NULL,
  geometry_type_name TEXT NOT NULL,
  srs_id INTEGER NOT NULL,
  z TINYINT NOT NULL,
  m TINYINT NOT NULL,
  CONSTRAINT pk_geom_cols PRIMARY KEY (table_name, column_name),
  CONSTRAINT uk_gc_table_name UNIQUE (table_name),
  CONSTRAINT fk_gc_tn FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
  CONSTRAINT fk_gc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id)
);
```

### gpkg_tile_matrix_set
```sql
CREATE TABLE gpkg_tile_matrix_set (
  table_name TEXT NOT NULL PRIMARY KEY,
  srs_id INTEGER NOT NULL,
  min_x DOUBLE NOT NULL,
  min_y DOUBLE NOT NULL,
  max_x DOUBLE NOT NULL,
  max_y DOUBLE NOT NULL,
  CONSTRAINT fk_gtms_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
  CONSTRAINT fk_gtms_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys (srs_id)
);
```

### gpkg_tile_matrix
```sql
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
  CONSTRAINT fk_tmm_table_name FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name)
);
```

### insert sample tile pyramid
```sql
CREATE TABLE sample_tile_pyramid (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zoom_level INTEGER NOT NULL,
  tile_column INTEGER NOT NULL,
  tile_row INTEGER NOT NULL,
  tile_data BLOB NOT NULL,
  UNIQUE (zoom_level, tile_column, tile_row)
)
```

### gpkg_extensions
```sql
CREATE TABLE gpkg_extensions (
  table_name TEXT,
  column_name TEXT,
  extension_name TEXT NOT NULL,
  definition TEXT NOT NULL,
  scope TEXT NOT NULL,
  CONSTRAINT ge_tce UNIQUE (table_name, column_name, extension_name)
);
```

### SQL trigger definition
```sql
CREATE TRIGGER 'gpkg_tile_matrix_zoom_level_insert'
BEFORE INSERT ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates constraint: zoom_level cannot be less than 0')
WHERE (NEW.zoom_level < 0);
END

CREATE TRIGGER 'gpkg_tile_matrix_zoom_level_update'
BEFORE UPDATE of zoom_level ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates constraint: zoom_level cannot be less than 0')
WHERE (NEW.zoom_level < 0);
END

CREATE TRIGGER 'gpkg_tile_matrix_matrix_width_insert'
BEFORE INSERT ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates constraint: matrix_width cannot be less than 1')
WHERE (NEW.matrix_width < 1);
END

CREATE TRIGGER 'gpkg_tile_matrix_matrix_width_update'
BEFORE UPDATE OF matrix_width ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates constraint: matrix_width cannot be less than 1')
WHERE (NEW.matrix_width < 1);
END

CREATE TRIGGER 'gpkg_tile_matrix_matrix_height_insert'
BEFORE INSERT ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates constraint: matrix_height cannot be less than 1')
WHERE (NEW.matrix_height < 1);
END

CREATE TRIGGER 'gpkg_tile_matrix_matrix_height_update'
BEFORE UPDATE OF matrix_height ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates constraint: matrix_height cannot be less than 1')
WHERE (NEW.matrix_height < 1);
END

CREATE TRIGGER 'gpkg_tile_matrix_pixel_x_size_insert'
BEFORE INSERT ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates constraint: pixel_x_size must be greater than 0')
WHERE NOT (NEW.pixel_x_size > 0);
END

CREATE TRIGGER 'gpkg_tile_matrix_pixel_x_size_update'
BEFORE UPDATE OF pixel_x_size ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates constraint: pixel_x_size must be greater than 0')
WHERE NOT (NEW.pixel_x_size > 0);
END

CREATE TRIGGER 'gpkg_tile_matrix_pixel_y_size_insert'
BEFORE INSERT ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'insert on table ''gpkg_tile_matrix'' violates constraint: pixel_y_size must be greater than 0')
WHERE NOT (NEW.pixel_y_size > 0);
END

CREATE TRIGGER 'gpkg_tile_matrix_pixel_y_size_update'
BEFORE UPDATE OF pixel_y_size ON 'gpkg_tile_matrix'
FOR EACH ROW BEGIN
SELECT RAISE(ABORT, 'update on table ''gpkg_tile_matrix'' violates constraint: pixel_y_size must be greater than 0')
WHERE NOT (NEW.pixel_y_size > 0);
END
```
