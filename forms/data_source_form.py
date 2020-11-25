from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField, TextAreaField,\
    ValidationError
from wtforms.validators import DataRequired


class DataSourceForm(FlaskForm):
    connection_type = SelectField('Typ', choices=[
        ('database', "Datenbank"),
        ('directory', "Filebasiert"),
        ('wms', "WMS"),
        ('wmts', "WMTS")
    ])
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    responsible = SelectField(
        'Verantwortlicher', coerce=int,
        validators=[DataRequired(message="Kein Verantwortlicher ausgewählt")]
    )
    connection = StringField('DB Connection', validators=[DataRequired()])

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.DataSource = self.config_models.model('data_source')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(DataSourceForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if DataSource name exists
        session = self.config_models.session()
        query = session.query(self.DataSource).filter_by(name=field.data)
        if self.obj:
            # ignore current data_source
            query = query.filter(self.DataSource.gdi_oid != self.obj.gdi_oid)
        data_source = query.first()
        session.close()

        if data_source is not None:
            raise ValidationError(
                'Eine DataSource mit diesem Namen ist bereits vorhanden'
            )
