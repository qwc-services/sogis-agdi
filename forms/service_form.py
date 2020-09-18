from flask import json
from flask_wtf import FlaskForm
from wtforms import BooleanField, FieldList, FormField, HiddenField, \
    SelectField, StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class DataProductForm(FlaskForm):
    """Subform for data products"""
    data_product_id = HiddenField('DataProduct-ID', validators=[DataRequired()])
    data_product_name = HiddenField('DataProduct', validators=[Optional()])


class ServiceModuleForm(FlaskForm):
    """Subform for services"""
    service_module_id = HiddenField('Module-ID', validators=[DataRequired()])
    service_module_name = HiddenField('Module', validators=[Optional()])


class ServiceForm(FlaskForm):
    """Main form for Service GUI"""
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    responsible = SelectField(
        'Verantwortlicher', coerce=int,
        validators=[DataRequired(message="Kein Verantwortlicher ausgewählt")]
    )
    url = StringField('URL', validators=[DataRequired()])
    specific_source = BooleanField('Specific source')

    data_products = FieldList(FormField(DataProductForm))
    data_product = SelectField(
        'Verwendete DataProducts', coerce=int, validators=[Optional()]
    )
    service_modules = FieldList(FormField(ServiceModuleForm))
    service_module = SelectField(
        'Verwendete Modules', coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Service = self.config_models.model('service')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(ServiceForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if Service name exists
        session = self.config_models.session()
        query = session.query(self.Service).filter_by(name=field.data)
        if self.obj:
            # ignore current service
            query = query.filter(self.Service.gdi_oid != self.obj.gdi_oid)
        service = query.first()
        session.close()

        if service is not None:
            raise ValidationError(
                'Ein Service mit diesem Namen ist bereits vorhanden'
            )
