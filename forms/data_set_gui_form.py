import re

from flask_wtf import FlaskForm
from werkzeug.datastructures import FileStorage
from wtforms import *
from wtforms.widgets.html5 import NumberInput
from wtforms.validators import DataRequired, Optional, Regexp, NumberRange,\
    InputRequired


class JSONAttributeForm(FlaskForm):
    name = HiddenField('Name', validators=[DataRequired()])
    alias = StringField('Alias', validators=[Optional()])
    active = BooleanField()


class AttributeForm(FlaskForm):
    """Subform for attributes"""
    name = HiddenField('Name', validators=[DataRequired()])
    alias = StringField('Alias', validators=[Optional()])
    format = StringField('Format', validators=[Optional()])
    active = BooleanField()
    displayfield = BooleanField()
    attr_order = HiddenField('Reihenfolge', validators=[DataRequired()])
    json_attrs = FieldList(FormField(JSONAttributeForm))


class PermissionForm(FlaskForm):
    """Subform for permissions"""
    role_id = HiddenField('Rollen-ID', validators=[DataRequired()])
    role_name = HiddenField('Rolle', validators=[Optional()])
    read = BooleanField('Lesen')
    write = BooleanField('Schreiben')


class DataSetGUIForm(FlaskForm):
    """Main form for DataSet GUI"""
    connection_type = SelectField(
        'Typ',
        choices=[
            ('database', "PostGIS Datenbank"),
            ('basic_database', "andere Datenbank"),
            ('directory', "Filebasiert")
        ],
        default='database'
    )
    name = StringField(
        'Identifier',
        validators=[
            DataRequired(),
            Regexp(r'^\S+$', message="Name darf keine Leerzeichen enthalten")
        ]
    )
    title = StringField('Titel', validators=[Optional()])
    synonyms = StringField('Synonyme', validators=[Optional()])
    abstract = TextAreaField('Beschreibung', validators=[Optional()])
    keywords = StringField('Stichworte', validators=[Optional()])
    description = TextAreaField(
        'Bemerkung intern', validators=[DataRequired()]
    )
    feature_id_column = StringField(
        'Feldname Feature-ID', validators=[Optional()]
    )
    facet = StringField('Solr Facet', validators=[Optional()])
    filter_word = StringField('Filter-Word', validators=[Optional()])
    data_owner = SelectField(
        'Datenherr', coerce=int,
        validators=[DataRequired(message="Kein Datenherr ausgewählt")]
    )

    data_source = SelectField(
        'Datasource', coerce=int, choices=[], validators=[Optional()]
    )
    db_table = SelectField(
        'DB Entität', choices=[], validators=[Optional()]
    )
    db_alert_title = None
    db_alert_msg = None

    raster_data_source = SelectField(
        'Datasource', coerce=int, choices=[], validators=[Optional()]
    )
    raster_data_set = SelectField(
        'Rasterlayer', choices=[], validators=[Optional()]
    )

    basic_data_source = SelectField(
        'Datasource', coerce=int, choices=[], validators=[Optional()]
    )
    basic_db_table = StringField(
        'DB Entität', validators=[Optional()]
    )

    primary_key_required = False
    primary_key = StringField('Primary Key für View', validators=[Optional()])

    geom_column = SelectField(
        'Geometriespalte', choices=[], validators=[Optional()]
    )

    searchable = SelectField(
        'Suchbar',
        coerce=int,
        choices=[
            (0, "Nein"),
            (1, "Wenn geladen"),
            (2, "Immer")
        ],
        default=0
    )
    in_wms = BooleanField('In WMS verfügbar')
    in_wfs = BooleanField('In WFS verfügbar')
    info_template = SelectField('Spezieller Infobutton', coerce=int)
    object_sheet = SelectField('Objektblatt', coerce=int)
    legend_file = FileField('Spezielle Legende')
    legend_present = False
    remove_legend = BooleanField('Vorhandene Legende entfernen')
    qml_file = FileField(
        'Darstellungen Server',
        description="QML oder ZIP mit QML und Symbolen auswählen"
    )
    qml_present = False
    remove_qml = BooleanField('Vorhandene Darstellungen Server entfernen')
    client_qml_file = FileField(
        'Darstellungen Client',
        description="QML oder ZIP mit QML und Symbolen auswählen"
    )
    client_qml_present = False
    remove_client_qml = BooleanField(
        'Vorhandene Darstellungen Client entfernen'
    )
    transparency = IntegerField(
        'Transparenz',
        widget=NumberInput(),
        validators=[
            Optional(),
            NumberRange(
                min=0, max=100, message='Wert muss zwischen 0 und 100 liegen'
            )
        ]
    )
    attrs = FieldList(FormField(AttributeForm))
    permissions = FieldList(FormField(PermissionForm))
    role = SelectField('Rolle', coerce=int, validators=[Optional()])
    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.DataSetView = self.config_models.model('data_set_view')
        self.OWSLayerGroup = self.config_models.model('ows_layer_group')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(DataSetGUIForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of DataSet and ProductSet name"""
        session = self.config_models.session()

        # check if DataSet name exists
        query = session.query(self.DataSetView).filter_by(name=field.data)
        if self.obj:
            # ignore current data_set_view
            query = query.filter(self.DataSetView.gdi_oid != self.obj.gdi_oid)
        data_set_view = query.first()

        # check if ProductSet name exists
        query = session.query(self.OWSLayerGroup).filter_by(name=field.data)
        ows_layer_group = query.first()

        session.close()

        if data_set_view is not None:
            raise ValidationError(
                'Ein DataSet mit diesem Namen ist bereits vorhanden'
            )
        if ows_layer_group is not None:
            raise ValidationError(
                'Ein ProductSet mit diesem Namen ist bereits vorhanden'
            )

    def validate_qml_file(self, field):
        """Validate QML file upload."""
        if isinstance(field.data, FileStorage):
            if field.data.filename:
                # check file extension
                ext_pattern = re.compile("^[^\/\\\\]+\.(qml|zip)$")
                if not ext_pattern.match(field.data.filename):
                    raise ValidationError('Datei ist kein QML oder ZIP')
