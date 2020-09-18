from .controller import Controller
from forms import UserForm


class UsersController(Controller):
    """Controller for user model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(UsersController, self).__init__(
            "Benutzer", 'users', 'user', 'users', app, config_models
        )
        self.User = self.config_models.model('user')
        self.Group = self.config_models.model('group')
        self.Role = self.config_models.model('role')

    def resources_for_index(self, session):
        """Return users list.

        :param Session session: DB session
        """
        return session.query(self.User).order_by(self.User.name).all()

    def form_for_new(self):
        """Return form for new user."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating User."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new User records in DB.

        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find User by ID.

        :param int id: User ID
        :param Session session: DB session
        """
        return session.query(self.User).filter_by(id=id).first()

    def form_for_edit(self, resource):
        """Return form for editing User.

        :param object resource: User object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating User.

        :param object resource: user object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing User records in DB.

        :param object resource: user object
        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional user object
        :param bool edit_form: Set if edit form
        """
        form = UserForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_groups(resource, edit_form, form, session)
        self.update_form_roles(resource, edit_form, form, session)
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update User records in DB.

        :param object resource: Optional user object
                                (None for create)
        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        if resource is None:
            # create new user
            user = self.User()
            session.add(user)
        else:
            # update existing user
            user = resource

        # update user
        user.name = form.name.data
        user.description = form.description.data

        # update groups
        self.update_collection(
            user.group_collection, form.groups, 'group_id', self.Group, 'id',
            session
        )
        # update roles
        self.update_collection(
            user.role_collection, form.roles, 'role_id', self.Role, 'id',
            session
        )

    def update_form_groups(self, user, edit_form, form, session):
        """Update groups subform for group.

        :param object module: Optional user object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        if edit_form:
            # add groups for resource on edit
            for group in user.sorted_groups:
                form.groups.append_entry({
                    'group_id': group.id,
                    'group_name': group.name,
                })

        # load related resources from DB
        query = session.query(self.Group).order_by(self.Group.name)
        groups = query.all()

        # set choices for group select field
        form.group.choices = [(0, "")] + [
            (g.id, g.name) for g in groups
        ]

    def update_form_roles(self, user, edit_form, form, session):
        """Update roles subform for user.

        :param object module: Optional user object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        if edit_form:
            # add roles for resource on edit
            for role in user.sorted_roles:
                form.roles.append_entry({
                    'role_id': role.id,
                    'role_name': role.name,
                })

        # load related resources from DB
        query = session.query(self.Role).order_by(self.Role.name)
        roles = query.all()

        # set choices for role select field
        form.role.choices = [(0, "")] + [
            (u.id, u.name) for u in roles
        ]
