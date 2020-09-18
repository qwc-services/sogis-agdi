from .controller import Controller
from forms import GroupForm


class GroupsController(Controller):
    """Controller for group model"""

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(GroupsController, self).__init__(
            "Gruppe", 'groups', 'group', 'groups', app, config_models
        )
        self.Group = self.config_models.model('group')
        self.User = self.config_models.model('user')
        self.Role = self.config_models.model('role')

    def resources_for_index(self, session):
        """Return groups list.

        :param Session session: DB session
        """
        return session.query(self.Group).order_by(self.Group.name).all()

    def form_for_new(self):
        """Return form for new group."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Group."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Group records in DB.

        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Group by ID.

        :param int id: Group ID
        :param Session session: DB session
        """
        return session.query(self.Group).filter_by(id=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Group.

        :param object resource: Group object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Group.

        :param object resource: group object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Group records in DB.

        :param object resource: group object
        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional group object
        :param bool edit_form: Set if edit form
        """
        form = GroupForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_users(resource, edit_form, form, session)
        self.update_form_roles(resource, edit_form, form, session)
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Group records in DB.

        :param object resource: Optional group object
                                (None for create)
        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        if resource is None:
            # create new group
            group = self.Group()
            session.add(group)
        else:
            # update existing group
            group = resource

        # update group
        group.name = form.name.data
        group.description = form.description.data

        # update users
        self.update_collection(
            group.user_collection, form.users, 'user_id', self.User, 'id',
            session
        )
        # update roles
        self.update_collection(
            group.role_collection, form.roles, 'role_id', self.Role, 'id',
            session
        )

    def update_form_users(self, group, edit_form, form, session):
        """Update users subform for group.

        :param object module: Optional group object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        if edit_form:
            # add users for resource on edit
            for user in group.sorted_users:
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

    def update_form_roles(self, group, edit_form, form, session):
        """Update roles subform for group.

        :param object module: Optional group object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Group
        :param Session session: DB session
        """
        if edit_form:
            # add roles for resource on edit
            for role in group.sorted_roles:
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
