from flask_wtf import FlaskForm
from wtforms import BooleanField, FieldList, FileField, FormField, \
    HiddenField, IntegerField, SelectField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired, NumberRange, Optional, Regexp


class MapLayerForm(FlaskForm):
    """Subform for map layers"""
    layer_id = HiddenField('Layer-ID', validators=[DataRequired()])
    layer_name = HiddenField('DataProduct', validators=[Optional()])
    layer_transparency = IntegerField(
        'Transparenz', validators=[NumberRange(min=0, max=100)]
    )
    layer_active = BooleanField('Sichtbarkeit')
    layer_order = HiddenField('Reihenfolge', validators=[DataRequired()])


class PermissionForm(FlaskForm):
    """Subform for permissions"""
    role_id = HiddenField('Rollen-ID', validators=[DataRequired()])
    role_name = HiddenField('Rolle', validators=[Optional()])
    read = BooleanField('Lesen')


class MapForm(FlaskForm):
    title = StringField(
        'Titel', description="Titel im Viewer", validators=[DataRequired()]
    )
    name = StringField(
        'Name', description="Name für Permalink", validators=[DataRequired()]
    )
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    responsible = SelectField(
        'Verantwortlicher', coerce=int,
        validators=[DataRequired(message="Kein Verantwortlicher ausgewählt")]
    )
    sublayers = FieldList(FormField(MapLayerForm))
    layer = SelectField('Layer', coerce=int, validators=[Optional()])
    background_layer = SelectField(
        'Default BackgroundLayer', coerce=int, validators=[Optional()]
    )
    initial_extent = StringField(
        'Extent',
        validators=[
            DataRequired(),
            Regexp(
                r'\d+(\.\d+)?,\s*\d+(\.\d+)?,\s*\d+(\.\d+)?,\s*\d+(\.\d+)?',
                message="Extent nicht im Format <minx>,<miny>,<maxx>,<maxy>"
            )
        ]
    )
    initial_scale = IntegerField(
        'Massstab',
        validators=[
            Optional(),
            NumberRange(min=1, message="Massstab muss grösser 0 sein")
        ]
    )
    thumbnail_file = FileField('Vorschaubild')
    thumbnail_present = False
    remove_thumbnail = BooleanField('Vorhandenes Vorschaubild entfernen')
    permissions = FieldList(FormField(PermissionForm))
    role = SelectField('Rolle', coerce=int, validators=[Optional()])

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Map = self.config_models.model('map')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(MapForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if Map name exists
        session = self.config_models.session()
        query = session.query(self.Map).filter_by(name=field.data)
        if self.obj:
            # ignore current map
            query = query.filter(self.Map.gdi_oid != self.obj.gdi_oid)
        map_obj = query.first()
        session.close()

        if map_obj is not None:
            raise ValidationError(
                'Eine Map mit diesem Namen ist bereits vorhanden'
            )
