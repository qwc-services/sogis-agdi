from flask_wtf import FlaskForm
from werkzeug.datastructures import FileStorage
from wtforms import BooleanField, FieldList, FileField, FormField, \
    HiddenField, SelectField, StringField, SubmitField, TextAreaField, \
    ValidationError
from wtforms.validators import DataRequired, Optional


class SubLayerForm(FlaskForm):
    """Subform for sub layers"""
    layer_id = HiddenField('Layer-ID', validators=[DataRequired()])
    layer_name = HiddenField('Layer', validators=[Optional()])
    layer_active = BooleanField()
    layer_order = HiddenField('Reihenfolge', validators=[DataRequired()])


class ProductSetGUIForm(FlaskForm):
    """Main form for ProductSet GUI"""
    name = StringField('Identifier', validators=[DataRequired()])
    title = StringField('Titel', validators=[DataRequired()])
    synonyms = StringField('Synonyme', validators=[Optional()])
    abstract = TextAreaField('Beschreibung', validators=[Optional()])
    keywords = StringField('Stichworte', validators=[Optional()])
    description = TextAreaField(
        'Bemerkung intern', validators=[DataRequired()]
    )
    feature_id_column = StringField(
        'Feldname Feature-ID', validators=[Optional()]
    )
    data_owner = SelectField(
        'Datenherr', coerce=int,
        validators=[DataRequired(message="Kein Datenherr ausgewählt")]
    )

    # NOTE: use 'sublayers' as field name to avoid conflict with
    #       'sub_layers' from OWSLayerGroup model
    sublayers = FieldList(FormField(SubLayerForm))
    layer = SelectField('Layer', coerce=int, validators=[Optional()])

    in_wms = BooleanField('In WMS verfügbar')
    in_wfs = BooleanField('In WFS verfügbar')
    facade = BooleanField('Facadelayer')
    legend_file = FileField('Spezielle Legende')
    legend_present = False
    remove_legend = BooleanField('Vorhandene Legende entfernen')

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

        super(ProductSetGUIForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of DataSet and ProductSet name"""
        session = self.config_models.session()

        # check if DataSet name exists
        query = session.query(self.DataSetView).filter_by(name=field.data)
        data_set_view = query.first()

        # check if ProductSet name exists
        query = session.query(self.OWSLayerGroup).filter_by(name=field.data)
        if self.obj:
            # ignore current ows_layer_data
            query = query.filter(
                self.OWSLayerGroup.gdi_oid != self.obj.gdi_oid
            )
        ows_layer_group = query.first()

        # allow identical names for WMS and WFS root layers
        skip_root_layers = (
            ows_layer_group and self.obj and ows_layer_group.wms_wfs_collection
            and self.obj.wms_wfs_collection
        )

        session.close()

        if data_set_view is not None:
            raise ValidationError(
                'Ein DataSet mit diesem Namen ist bereits vorhanden'
            )
        if ows_layer_group is not None and not skip_root_layers:
            raise ValidationError(
                'Ein ProductSet mit diesem Namen ist bereits vorhanden'
            )
