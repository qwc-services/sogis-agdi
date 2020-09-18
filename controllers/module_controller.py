from .contacts_helper import ContactsHelper
from .controller import Controller
from forms import ModuleForm


class ModuleController(Controller):
    """Controller for Module GUI

    Manage module from GUI.
    """

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(ModuleController, self).__init__(
            "Module", 'module', 'module',
            'module', app, config_models
        )
        self.ContactsHelper = ContactsHelper(config_models, app.logger)

        self.Module = self.config_models.model('module')
        self.DataSetView = self.config_models.model('data_set_view')
        self.OWSLayerGroup = self.config_models.model('ows_layer_group')
        self.GDIResource = self.config_models.model('gdi_resource')
        self.Service = self.config_models.model('service')

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return modules list.

        :param Session session: DB session
        """
        return session.query(self.Module).order_by(self.Module.name).all()

    def form_for_new(self):
        """Return form for new Module."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Module."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Module records in DB.

        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Module by ID.

        :param int id: Module ID
        :param Session session: DB session
        """
        return session.query(self.Module).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Module.

        :param object resource: Module object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Module.

        :param object resource: module object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Module records in DB.

        :param object resource: module object
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional module object
        :param bool edit_form: Set if edit form
        """
        form = ModuleForm(self.config_models, obj=resource)

        session = self.session()
        self.update_form_resource_contacts(resource, edit_form, form)
        self.update_form_data_products(resource, edit_form, form, session)
        self.update_form_module_services(resource, edit_form, form, session)
        session.close()

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Module records in DB.

        :param object resource: Optional module object
                                (None for create)
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        if resource is None:
            # create new module
            module = self.Module()
            session.add(module)
        else:
            # update existing module
            module = resource

        # update module
        module.name = form.name.data
        module.description = form.description.data
        module.url = form.url.data

        self.update_resource_contacts(module, form, session)
        self.update_data_products(module, form, session)
        self.update_module_services(module, form, session)

    def destroy_resource(self, resource, session):
        """Delete existing Module records in DB.

        :param object resource: module object
        :param Session session: DB session
        """
        # remove module and resource contacts
        module = resource
        self.ContactsHelper.remove_resource_contacts(
            module.gdi_oid, session
        )
        session.delete(module)

    def update_form_resource_contacts(self, module, edit_form, form):
        """Update data products subform for resource.

        :param object module: Optional module object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Module
        """
        if edit_form:
            # select responsible contact
            form.responsible.data = self.ContactsHelper.resource_contact_id(
                module.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE
            )

            # select supplier contact
            form.supplier.data = self.ContactsHelper.resource_contact_id(
                module.gdi_oid, self.ContactsHelper.ROLE_SUPPLIER
            )

        # set choices for responsible select field
        form.responsible.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        # set choices for supplier select field
        form.supplier.choices = [(0, "")] + \
            self.ContactsHelper.contact_choices()

    def update_form_data_products(self, module, edit_form, form, session):
        """Update data products subform for resource.

        :param object module: Optional module object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        if edit_form:
            # add data products for resource on edit
            for data_product in module.sorted_data_products:
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

    def update_form_module_services(self, module, edit_form, form, session):
        """Update services subform for resource.

        :param object module: Optional module object
        :param bool edit_form: Set if edit form
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        if edit_form:
            # add services for resource on edit
            for module_service in module.services:
                form.module_services.append_entry({
                    'module_service_id': module_service.gdi_oid,
                    'module_service_name': module_service.name,
                })

        # load related resources from DB
        query = session.query(self.Service).order_by(self.Service.name)
        module_services = query.all()

        # set choices for services select field
        form.module_service.choices = [(0, "")] + [
            (d.gdi_oid, d.name) for d in module_services
        ]

    def update_resource_contacts(self, module, form, session):
        """Update resource contacts for module.

        :param object module: module object
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """
        # NOTE: flush object changes in session to update gdi_oid of a
        #       new module
        session.flush()

        # update responsible contacts
        self.ContactsHelper.update_resource_contact(
            module.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE,
            form.responsible.data, session
        )
        # update supplier contact
        self.ContactsHelper.update_resource_contact(
            module.gdi_oid, self.ContactsHelper.ROLE_SUPPLIER,
            form.supplier.data, session
        )

    def update_data_products(self, module, form, session):
        """Add or remove data products for module.

        :param object module: module object
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """

        # lookup for gdi_resource of module
        module_data_products = {}
        for data_product in module.sorted_data_products:
            module_data_products[data_product.gdi_oid] = data_product

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
                if data_product_id not in module_data_products:
                    # add gdi_resource to module
                    module.sorted_data_products.append(data_product)

        # remove removed data products
        for data_product in module_data_products.values():
            if data_product.gdi_oid not in data_product_ids:
                # remove gdi_resource from module
                module.sorted_data_products.remove(data_product)

    def update_module_services(self, module, form, session):
        """Add or remove services for module.

        :param object module: module object
        :param FlaskForm form: Form for Module
        :param Session session: DB session
        """

        # lookup for service of module
        module_services = {}
        for module_service in module.services:
            module_services[module_service.gdi_oid] = module_service

        # update services
        module_service_ids = []
        for module_service in form.module_services:
            # get service from ConfigDB
            module_service_id = int(module_service.data['module_service_id'])
            query = session.query(self.Service) \
                .filter_by(gdi_oid=module_service_id)
            module_service = query.first()

            if module_service is not None:
                module_service_ids.append(module_service_id)
                if module_service_id not in module_services:
                    # add module_service to module
                    module.services.append(module_service)

        # remove removed services
        for module_service in module_services.values():
            if module_service.gdi_oid not in module_service_ids:
                # remove service from module
                module.services.remove(module_service)
