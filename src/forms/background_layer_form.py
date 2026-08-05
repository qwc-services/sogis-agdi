from flask import json
from flask_wtf import FlaskForm
from wtforms import BooleanField, FileField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired


class BackgroundLayerForm(FlaskForm):
    name = StringField('Name',
                       description="Hinweis: Mit einem Nummernprefix vor dem Namen kann die Reihenfolge kontrolliert werden",
                       validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    qgis_datasource = StringField(
        'QGIS Datasource',
        description="WMS/WMTS Layerquelle für QGIS Projekt",
        validators=[DataRequired()]
    )
    thumbnail_file = FileField('Vorschaubild')
    thumbnail_present = False
    remove_thumbnail = BooleanField('Vorhandenes Vorschaubild entfernen')
    qwc2_bg_layer_config = TextAreaField(
        'QWC2 Config',
        description="JSON Config für einen BackgroundLayer in QWC2 themes.json",
        validators=[DataRequired()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.BackgroundLayer = self.config_models.model('background_layer')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(BackgroundLayerForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if BackgroundLayer name exists
        session = self.config_models.session()
        query = session.query(self.BackgroundLayer).filter_by(name=field.data)
        if self.obj:
            # ignore current background_layer
            query = query.filter(
                self.BackgroundLayer.gdi_oid != self.obj.gdi_oid
            )
        background_layer = query.first()
        session.close()

        if background_layer is not None:
            raise ValidationError(
                'Ein BackgroundLayer mit diesem Namen ist bereits vorhanden'
            )

    def validate_qwc2_bg_layer_config(self, field):
        """Validate QWC2 config"""
        if field.data:
            try:
                # validate JSON
                json.loads(field.data)
            except ValueError as e:
                raise ValidationError('Ungültiges JSON: %s' % e)
