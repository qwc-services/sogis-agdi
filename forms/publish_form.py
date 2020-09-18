import re

from flask_wtf import FlaskForm
from wtforms import BooleanField, SubmitField


class PublishForm(FlaskForm):
    service_configs = BooleanField(
        'Service Configs und Permissions', default="y"
    )
    wms_wfs = BooleanField('WMS/WFS', default="y")
    solr_index = BooleanField('Solr Metadaten', default="y")
    submit = SubmitField('Speichern')
