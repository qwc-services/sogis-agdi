import os
import sys

from flask import Flask, jsonify, render_template
from flask_bootstrap import Bootstrap
from flask_wtf.csrf import CSRFProtect

from controllers import DataSourcesController, DataSetGUIController,\
    ProductSetGUIController, BackgroundLayersController, MapsController,\
    TemplatesController, UsersController, GroupsController, RolesController, \
    ServiceController, ModuleController, TransformationController, \
    WmsWfsController, ContactsController, PublishController

from qwc_services_core.runtime_config import RuntimeConfig
from qwc_services_core.tenant_handler import TenantHandler
from service_lib.auth import auth_manager, optional_auth, get_auth_user
from service_lib.database import DatabaseEngine
from service_lib.config_models import ConfigModels


# Flask application
app = Flask(__name__)

auth = auth_manager(app)

app.secret_key = os.environ.get(
        'JWT_SECRET_KEY',
        'CHANGE-ME-1ef43ade8807dc37a6588cb8fb9dec4caf6dfd0e00398f9a')

# enable CSRF protection
csrf = CSRFProtect(app)
# load Bootstrap extension
Bootstrap(app)

# create tenant and config handlers
tenant_handler = TenantHandler(app.logger)
config_handler = RuntimeConfig('agdi', app.logger)


def service_config():
    """Return service config from cache or from config file.

    NOTE: read config from file only if config has changed
    """
    tenant = tenant_handler.tenant()
    config = tenant_handler.handler('agdi', 'agdi', tenant)
    if config is None:
        # load current service config
        service_config = config_handler.tenant_config(tenant)
        # register as handler to chache it
        config = tenant_handler.register_handler(
            'agdi', tenant, service_config
        )
    return config


# get config DB connnection from service config
# NOTE: this is loaded only once when the AGDI GUI application
#       is started and will not be updated if the config changes later
config_db_url = service_config().get(
    'db_url', 'postgresql:///?service=soconfig_services'
)

try:
    # load ORM models for ConfigDB
    db_engine = DatabaseEngine()
    config_db_engine = db_engine.db_engine(config_db_url)
    config_models = ConfigModels(config_db_engine)
except Exception as e:
    msg = (
        "Could not load ConfigModels for ConfigDB at '%s':\n%s" %
        (config_db_url, e)
    )
    app.logger.error(msg)
    raise Exception(msg)


# create controllers (including their routes)
# gdi_knoten
DataSourcesController(app, config_models)
DataSetGUIController(app, config_models, db_engine, service_config)
ProductSetGUIController(app, config_models)
BackgroundLayersController(app, config_models, service_config)
MapsController(app, config_models, service_config)
TemplatesController(app, config_models, service_config)
ServiceController(app, config_models)
ModuleController(app, config_models)
TransformationController(app, config_models, db_engine)
wms_wfs_controller = WmsWfsController(app, config_models, db_engine)
PublishController(app, config_models, service_config)
# iam
UsersController(app, config_models)
GroupsController(app, config_models)
RolesController(app, config_models)
# contacts
ContactsController(app, config_models)


# routes
@app.route('/')
@optional_auth
def home():
    # show WMS/WFS page as root
    return wms_wfs_controller.edit()


""" readyness probe endpoint """
@app.route("/ready", methods=['GET'])
def ready():
    return jsonify({"status": "OK"})


""" liveness probe endpoint """
@app.route("/healthz", methods=['GET'])
def healthz():
    return jsonify({"status": "OK"})


# local webserver
if __name__ == '__main__':
    print("Starting AGDI service...")
    app.run(host='localhost', port=5031, debug=True)
