from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class UserForm(FlaskForm):
    """Subform for users"""
    user_id = HiddenField('Benutzer-ID', validators=[DataRequired()])
    user_name = HiddenField('Benutzer', validators=[Optional()])


class RoleForm(FlaskForm):
    """Subform for roles"""
    role_id = HiddenField('Rollen-ID', validators=[DataRequired()])
    role_name = HiddenField('Rolle', validators=[Optional()])


class GroupForm(FlaskForm):
    """Main form for Group GUI"""
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    users = FieldList(FormField(UserForm))
    user = SelectField(
        'Zugeordnete Benutzer', coerce=int, validators=[Optional()]
    )
    roles = FieldList(FormField(RoleForm))
    role = SelectField(
        'Zugeordnete Rollen', coerce=int, validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.Group = self.config_models.model('group')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(GroupForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if Group name exists
        session = self.config_models.session()
        query = session.query(self.Group).filter_by(name=field.data)
        if self.obj:
            # ignore current group
            query = query.filter(self.Group.id != self.obj.id)
        group = query.first()
        session.close()

        if group is not None:
            raise ValidationError(
                'Eine Gruppe mit diesem Namen ist bereits vorhanden'
            )
