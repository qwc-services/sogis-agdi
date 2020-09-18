from .contacts_helper import ContactsHelper
from .controller import Controller
from .permissions_helper import PermissionsHelper
from forms import DataSourceForm


class DataSourcesController(Controller):
    """Controller for DataSource GUI

    Manage data_source and related models from combined GUI.
    """

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(DataSourcesController, self).__init__(
            "DataSource", 'data_sources', 'data_source', 'data_sources', app,
            config_models
        )
        self.ContactsHelper = ContactsHelper(config_models, app.logger)
        self.PermissionsHelper = PermissionsHelper(config_models)
        self.DataSource = self.config_models.model('data_source')
        self.Person = self.config_models.model('person')

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return data sources list.

        :param Session session: DB session
        """
        return session.query(self.DataSource).order_by(self.DataSource.name) \
            .all()

    def form_for_new(self):
        """Return form for new data source."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating DataSource."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new DataSource records in DB.

        :param FlaskForm form: Form for DataSource
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find DataSource by DataSource ID.

        :param int id: DataSource ID
        :param Session session: DB session
        """
        return session.query(self.DataSource).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing DataSource.

        :param object resource: DataSource object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating DataSource.

        :param object resource: data_source object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing DataSource records in DB.

        :param object resource: data_source object
        :param FlaskForm form: Form for DataSource
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional data_source object
        :param bool edit_form: Set if edit form
        """
        form = DataSourceForm(self.config_models, obj=resource)

        if edit_form:
            # override form fields with resource values on edit
            form.responsible.data = self.ContactsHelper.resource_contact_id(
                resource.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE
            )

        # set choices for responsible select field
        form.responsible.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update DataSource records in DB.

        :param object resource: Optional data_source object
                                (None for create)
        :param FlaskForm form: Form for DataSource
        :param Session session: DB session
        """
        if resource is None:
            # create new data_source
            data_source = self.DataSource()
            session.add(data_source)
        else:
            # update existing data_source
            data_source = resource

        # update data_source
        data_source.connection_type = form.connection_type.data
        data_source.name = form.name.data
        data_source.description = form.description.data
        data_source.connection = form.connection.data

        # NOTE: flush object changes in session to update gdi_oid of a
        #       new data_source
        session.flush()

        # update resource contact
        self.ContactsHelper.update_resource_contact(
            data_source.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE,
            form.responsible.data, session
        )

        # add default public permission
        role = self.PermissionsHelper.public_role()
        if role is not None:
            self.PermissionsHelper.update_resource_permission(
                data_source.gdi_oid, role.id, True, False, session
            )

    def destroy_resource(self, resource, session):
        """Delete existing DataSource records in DB.

        :param object resource: data_source object
        :param Session session: DB session
        """
        # remove data_source, resource contacts and permissions
        data_source = resource
        self.ContactsHelper.remove_resource_contacts(
            data_source.gdi_oid, session)
        self.PermissionsHelper.remove_resource_permissions(
            data_source.gdi_oid, session
        )
        session.delete(data_source)
