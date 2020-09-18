from flask import json
from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class DataProductForm(FlaskForm):
    """Subform for data products"""
    data_product_id = HiddenField('DataProduct-ID', validators=[DataRequired()])
    data_product_name = HiddenField('DataProduct', validators=[Optional()])


class ModuleServiceForm(FlaskForm):
    """Subform for services"""
    module_service_id = HiddenField('Service-ID', validators=[DataRequired()])
    module_service_name = HiddenField('Service', validators=[Optional()])


class ModuleForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    responsible = SelectField(
        'Verantwortlicher', coerce=int,
        validators=[DataRequired(message="Kein Verantwortlicher ausgewählt")]
    )
    supplier = SelectField(
        'Externer Lieferant', coerce=int, validators=[Optional()]
    )
    url = StringField('URL', validators=[Optional()])

    data_products = FieldList(FormField(DataProductForm))
    data_product = SelectField(
        'Verwendete DataProducts', coerce=int, validators=[Optional()]
    )
    module_services = FieldList(FormField(ModuleServiceForm))
    module_service = SelectField(
        'Verwendete Services', coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Module = self.config_models.model('module')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(ModuleForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if Module name exists
        session = self.config_models.session()
        query = session.query(self.Module).filter_by(name=field.data)
        if self.obj:
            # ignore current module
            query = query.filter(self.Module.gdi_oid != self.obj.gdi_oid)
        module = query.first()
        session.close()

        if module is not None:
            raise ValidationError(
                'Ein Module mit diesem Namen ist bereits vorhanden'
            )
