from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import RoleForm


class RolesController(Controller):
    """Controller for role model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(RolesController, self).__init__(
            "Rolle", 'roles', 'role', 'roles', app, config_models
        )
        self.Role = self.config_models.model('role')
        self.User = self.config_models.model('user')
        self.Group = self.config_models.model('group')

    def resources_for_index(self, session):
        """Return roles list.

        :param Session session: DB session
        """
        return session.query(self.Role).order_by(self.Role.name).all()

    def form_for_new(self):
        """Return form for new role."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Role."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Role records in DB.

        :param FlaskForm form: Form for Role
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Role by ID.

        :param int id: Role ID
        :param Session session: DB session
        """
        return session.query(self.Role).filter_by(id=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Role.

        :param object resource: Role object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Role.

        :param object resource: role object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Role records in DB.

        :param object resource: role object
        :param FlaskForm form: Form for Role
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional role object
        :param bool edit_form: Set if edit form
        """
        form = RoleForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_groups(resource, edit_form, form, session)
        self.update_form_users(resource, edit_form, form, session)
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Role records in DB.

        :param object resource: Optional role object
                                (None for create)
        :param FlaskForm form: Form for Role
        :param Session session: DB session
        """
        if resource is None:
            # create new role
            role = self.Role()
            session.add(role)
        else:
            # update existing role
            role = resource

        # update role
        role.name = form.name.data
        role.description = form.description.data

        # update groups
        self.update_collection(
            role.group_collection, form.groups, 'group_id', self.Group, 'id',
            session
        )
        # update users
        self.update_collection(
            role.user_collection, form.users, 'user_id', self.User, 'id',
            session
        )

    def update_form_groups(self, role, edit_form, form, session):
        """Update groups subform for group.

        :param object module: Optional role object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for User
        :param Session session: DB session
        """
        if edit_form:
            # add groups for resource on edit
            for group in role.sorted_groups:
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

    def update_form_users(self, role, edit_form, form, session):
        """Update users subform for role.

        :param object module: Optional role object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        if edit_form:
            # add users for resource on edit
            for user in role.sorted_users:
                form.users.append_entry({
                    'user_id': user.id,
                    'user_name': user.name,
                })

        # load related resources from DB
        query = session.query(self.User).order_by(self.User.name)
        users = query.all()

        # set choices for user select field
        form.user.choices = [(0, "")] + [
            (u.id, u.name) for u in users
        ]
