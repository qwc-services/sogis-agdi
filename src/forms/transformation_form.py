from flask import json
from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class DataSetForm(FlaskForm):
    """Subform for data sets"""
    data_set_id = HiddenField('DataSet-ID', validators=[DataRequired()])
    data_set_name = HiddenField('Tabelle', validators=[Optional()])


class TransformationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    target_data_set = SelectField(
        'Ablageort', coerce=int, validators=[DataRequired()]
    )
    data_sets = FieldList(FormField(DataSetForm))
    source_data_set = SelectField(
        'Verwendete DataSets', coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Transformation = self.config_models.model('transformation')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(TransformationForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if Transformation name exists
        session = self.config_models.session()
        query = session.query(self.Transformation).filter_by(name=field.data)
        if self.obj:
            # ignore current transformation
            query = query.filter(
                self.Transformation.gdi_oid != self.obj.gdi_oid
            )
        transformation = query.first()
        session.close()

        if transformation is not None:
            raise ValidationError(
                'Eine Transformation mit diesem Namen ist bereits vorhanden'
            )

    def validate_data_sets(self, field):
        if not field.data:
            raise ValidationError('Kein DataSet ausgewählt')
