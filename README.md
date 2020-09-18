AGDI configuration backend
==========================

GUI for AGDI administration.


Dependencies
------------

* ConfigDB for managing GDI resources
* ConfigGenerator service for generating service configs and permissions, and writing QGIS project files
* Solr service for updating Solr Metadata index


Configuration
-------------

The static config file is stored as JSON files in `$CONFIG_PATH` with subdirectories for each tenant,
e.g. `$CONFIG_PATH/default/*.json`. The default tenant name is `default`.

### FeatureInfo Service config

* [JSON schema](../docs/schemas/sogis-agdi.json)
* File location: `$CONFIG_PATH/<tenant>/agdiConfig.json`

Example:
```json
{
  "$schema": "https://git.sourcepole.ch/ktso/somap/-/raw/master/docs/schemas/sogis-agdi.json",
  "service": "agdi",
  "config": {
    "db_url": "postgresql:///?service=soconfig_services",
    "project_output_dir": "../docker/volumes/qgs-resources/",
    "qwc_assets_dir": "../docker/volumes/qwc-assets/",
    "jasper_reports_dir": "../docker/volumes/jasper/reports/",
    "jasper_service_url": "http://localhost:8002/reports",
    "jasper_timeout": 60,
    "config_generator_url": "http://localhost:5032/",
    "solr_update_url": "http://localhost:8983/solr/gdi/dih_metadata?command=status"
  }
}
```

**NOTE:** Requires write permissions for AGDI docker user (`www-data`) in `project_output_dir` and `jasper_reports_dir` for uploading QMLs and symbols, generating QGS projects and uploading JasperReports reports.

### Environment variables

| Variable               | Description                                                            | Default value                            |
|------------------------|------------------------------------------------------------------------|------------------------------------------|
| `CONFIG_PATH`          | Path to directory containing service config file                       | `config`                                 |

### Volumes

QGIS projects are saved to `/qgs-resources` (using the ConfigGenerator service), with symbols in `/qgs-resources/symbols` and print resources in `/qgs-resources/print`.

Raster files for raster layers can be accessed from `/geodata`, which is also shared with the QGIS Server service.

JasperReports reports are saved to `/jasper/reports`, which is also shared with the Jasper Reporting service.


GUI Notes
---------

### DataSet GUI

QGIS layer style upload as ZIP containing a QML and any required custom symbol files. Missing symbols are assumed to be default QGIS symbols.

### BackgroundLayer GUI

QGIS Datasource is a string for A QGIS WMS/WMTS layer source, e.g.:

    contextualWMSLegend=0&crs=EPSG:2056&dpiMode=7&featureCount=10&format=image/png&layers=Grundkarte&styles=&url=https://geoweb.so.ch/wms/grundbuchplan

QWC2 Config is a JSON subconfig for a QWC2 background layer, e.g.:

    {
      "name": "Grundkarte",
      "title": "Grundkarte",
      "type": "wms",
      "url": "https://geoweb.so.ch/wms/grundbuchplan",
      "thumbnail": "img/mapthumbs/default.jpg"
    }

### Template GUI

QGIS print layout upload as ZIP containing a QPT and any required resources.


Usage/Development
-----------------

Set the `CONFIG_PATH` environment variable to the path containing the service config file when starting this service (default: `config`).

Start application:

    CONFIG_PATH=../docker/volumes/config/ python server.py

Admin GUI base URL:

    http://localhost:5031/
