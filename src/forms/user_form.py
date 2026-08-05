from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, HiddenField, SelectField, \
    StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class GroupForm(FlaskForm):
    """Subform for groups"""
    group_id = HiddenField('Gruppen-ID', validators=[DataRequired()])
    group_name = HiddenField('Gruppe', validators=[Optional()])


class RoleForm(FlaskForm):
    """Subform for roles"""
    role_id = HiddenField('Rollen-ID', validators=[DataRequired()])
    role_name = HiddenField('Rolle', validators=[Optional()])


class UserForm(FlaskForm):
    """Main form for User GUI"""
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    groups = FieldList(FormField(GroupForm))
    group = SelectField(
        'Zugeordnete Gruppen', coerce=int, validators=[Optional()]
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
        self.User = self.config_models.model('user')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(UserForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of name"""
        # check if user name exists
        session = self.config_models.session()
        query = session.query(self.User).filter_by(name=field.data)
        if self.obj:
            # ignore current user
            query = query.filter(self.User.id != self.obj.id)
        user = query.first()
        session.close()

        if user is not None:
            raise ValidationError(
                'Ein Benutzer mit diesem Namen ist bereits vorhanden'
            )
