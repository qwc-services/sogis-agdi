from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class GroupForm(FlaskForm):
    """Subform for groups"""
    group_id = HiddenField('Gruppen-ID', validators=[DataRequired()])
    group_name = HiddenField('Gruppe', validators=[Optional()])


class UserForm(FlaskForm):
    """Subform for users"""
    user_id = HiddenField('Benutzer-ID', validators=[DataRequired()])
    user_name = HiddenField('Benutzer', validators=[Optional()])


class RoleForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    groups = FieldList(FormField(GroupForm))
    group = SelectField(
        'Zugeordnete Gruppen', coerce=int, validators=[Optional()]
    )
    users = FieldList(FormField(UserForm))
    user = SelectField(
        'Zugeordnete Benutzer', coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Role = self.config_models.model('role')

        # store any provided role object
        self.obj = kwargs.get('obj')

        super(RoleForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if role name exists
        session = self.config_models.session()
        query = session.query(self.Role).filter_by(name=field.data)
        if self.obj:
            # ignore current role
            query = query.filter(self.Role.id != self.obj.id)
        role = query.first()
        session.close()

        if role is not None:
            raise ValidationError(
                'Eine Rolle mit diesem Namen ist bereits vorhanden'
            )
