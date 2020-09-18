from .contacts_helper import ContactsHelper
from .controller import Controller
from forms import ServiceForm


class ServiceController(Controller):
    """Controller for Service GUI

    Manage service from GUI.
    """

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(ServiceController, self).__init__(
            "Service", 'service', 'service',
            'service', app, config_models
        )
        self.ContactsHelper = ContactsHelper(config_models, app.logger)

        self.Service = self.config_models.model('service')
        self.DataSetView = self.config_models.model('data_set_view')
        self.OWSLayerGroup = self.config_models.model('ows_layer_group')
        self.GDIResource = self.config_models.model('gdi_resource')
        self.Module = self.config_models.model('module')

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return services list.

        :param Session session: DB session
        """
        return session.query(self.Service).order_by(self.Service.name).all()

    def form_for_new(self):
        """Return form for new Service."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Service."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Service records in DB.

        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Service by ID.

        :param int id: Service ID
        :param Session session: DB session
        """
        return session.query(self.Service).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Service.

        :param object resource: Service object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Service.

        :param object resource: service object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Service records in DB.

        :param object resource: service object
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional service object
        :param bool edit_form: Set if edit form
        """
        form = ServiceForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_resource_contacts(resource, edit_form, form)
        self.update_form_data_products(resource, edit_form, form, session)
        self.update_form_service_modules(resource, edit_form, form, session)
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Service records in DB.

        :param object resource: Optional service object
                                (None for create)
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        if resource is None:
            # create new service
            service = self.Service()
            session.add(service)
        else:
            # update existing service
            service = resource

        # update service
        service.name = form.name.data
        service.description = form.description.data
        service.url = form.url.data
        service.specific_source = form.specific_source.data

        self.update_resource_contacts(service, form, session)
        self.update_data_products(service, form, session)
        self.update_service_modules(service, form, session)

    def destroy_resource(self, resource, session):
        """Delete existing Service records in DB.

        :param object resource: service object
        :param Session session: DB session
        """
        # remove service and resource contact
        service = resource
        self.ContactsHelper.remove_resource_contacts(
            service.gdi_oid, session
        )
        session.delete(service)

    def update_form_resource_contacts(self, service, edit_form, form):
        """Update data products subform for resource.

        :param object service: Optional service object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Service
        """
        if edit_form:
            # select responsible contact
            form.responsible.data = self.ContactsHelper.resource_contact_id(
                service.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE
            )

        # set choices for responsible select field
        form.responsible.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

    def update_form_data_products(self, service, edit_form, form, session):
        """Update data products subform for resource.

        :param object service: Optional service object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        if edit_form:
            # add data products for resource on edit
            for data_product in service.sorted_data_products:
                form.data_products.append_entry({
                    'data_product_id': data_product.gdi_oid,
                    'data_product_name': data_product.name,
                })

        # load related resources from DB
        # get DataSets
        query = session.query(self.DataSetView).order_by(self.DataSetView.name)
        data_set_views = query.all()

        # get ProductSets
        query = session.query(self.OWSLayerGroup) \
            .order_by(self.OWSLayerGroup.name)
        ows_layer_groups = query.all()

        # order by name
        data_products = data_set_views + ows_layer_groups
        data_products.sort(key=lambda d: d.name.lower())

        # set choices for data product select field
        form.data_product.choices = [(0, "")] + [
            (d.gdi_oid, d.name) for d in data_products
        ]

    def update_form_service_modules(self, service, edit_form, form, session):
        """Update modules subform for resource.

        :param object service: Optional service object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        if edit_form:
            # add modules for resource on edit
            for service_module in service.modules:
                form.service_modules.append_entry({
                    'service_module_id': service_module.gdi_oid,
                    'service_module_name': service_module.name,
                })

        # load related resources from DB
        query = session.query(self.Module).order_by(self.Module.name)
        service_modules = query.all()

        # set choices for modules select field
        form.service_module.choices = [(0, "")] + [
            (d.gdi_oid, d.name) for d in service_modules
        ]

    def update_resource_contacts(self, service, form, session):
        """Update resource contact for service.

        :param object service: service object
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """
        # NOTE: flush object changes in session to update gdi_oid of a
        #       new service
        session.flush()

        # update resource contact
        self.ContactsHelper.update_resource_contact(
            service.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE,
            form.responsible.data, session
        )

    def update_data_products(self, service, form, session):
        """Add or remove data products for service.

        :param object service: service object
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """

        # lookup for gdi_resource of service
        service_data_products = {}
        for data_product in service.sorted_data_products:
            service_data_products[data_product.gdi_oid] = data_product

        # update data products
        data_product_ids = []
        for data_product in form.data_products:
            # get gdi_resource from ConfigDB
            data_product_id = int(data_product.data['data_product_id'])
            query = session.query(self.GDIResource) \
                .filter_by(gdi_oid=data_product_id)
            data_product = query.first()

            if data_product is not None:
                data_product_ids.append(data_product_id)
                if data_product_id not in service_data_products:
                    # add gdi_resource to service
                    service.sorted_data_products.append(data_product)

        # remove removed data products
        for data_product in service_data_products.values():
            if data_product.gdi_oid not in data_product_ids:
                # remove gdi_resource from service
                service.sorted_data_products.remove(data_product)

    def update_service_modules(self, service, form, session):
        """Add or remove modules for module.

        :param object service: service object
        :param FlaskForm form: Form for Service
        :param Session session: DB session
        """

        # lookup for service of service
        service_modules = {}
        for service_module in service.modules:
            service_modules[service_module.gdi_oid] = service_module

        # update services
        service_module_ids = []
        for service_module in form.service_modules:
            # get service from ConfigDB
            service_module_id = int(service_module.data['service_module_id'])
            query = session.query(self.Module) \
                .filter_by(gdi_oid=service_module_id)
            service_module = query.first()

            if service_module is not None:
                service_module_ids.append(service_module_id)
                if service_module_id not in service_modules:
                    # add service_module to service
                    service.modules.append(service_module)

        # remove removed modules
        for service_module in service_modules.values():
            if service_module.gdi_oid not in service_module_ids:
                # remove service from service
                service.modules.remove(service_module)
