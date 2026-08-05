from flask import flash, redirect, request, url_for
import os
import uuid


from .contacts_helper import ContactsHelper
from .controller import Controller
from .ows_helper import OWSHelper
from .permissions_helper import PermissionsHelper
from forms import MapForm


class MapsController(Controller):
    """Controller for Map GUI

    Manage maps and related models from combined GUI.
    """

    def __init__(self, app, config_models, service_config):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param func service_config: Helper method for reading service config
        """
        super(MapsController, self).__init__(
            "Map", 'maps', 'map', 'maps', app,
            config_models
        )
        self.service_config = service_config
        self.OWSHelper = OWSHelper(config_models)
        self.ContactsHelper = ContactsHelper(config_models, app.logger)
        self.PermissionsHelper = PermissionsHelper(config_models)

        self.Map = self.config_models.model('map')
        self.MapLayer = self.config_models.model('map_layer')
        self.BackgroundLayer = self.config_models.model('background_layer')
        self.WmsWfs = self.config_models.model('wms_wfs')

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # update map order
        app.add_url_rule(
            '/%s/map_order' % base_route,
            'map_order', self.update_map_order, methods=['POST']
        )

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return maps list.

        :param Session session: DB session
        """
        return session.query(self.Map) \
            .order_by(self.Map.map_order, self.Map.name).all()

    def form_for_new(self):
        """Return form for new Map."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Map."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Map records in DB.

        :param FlaskForm form: Form for Map
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Map by map ID.

        :param int id: map ID
        :param Session session: DB session
        """
        return session.query(self.Map).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Map.

        :param object resource: map object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Map.

        :param object resource: map object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Map records in DB.

        :param object resource: map object
        :param FlaskForm form: Form for Map
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional map object
        :param bool edit_form: Set if edit form
        """
        form = MapForm(self.config_models, obj=resource)

        if edit_form:
            # select responsible contact
            form.responsible.data = self.ContactsHelper.resource_contact_id(
                resource.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE
            )

            # add map layers for resource on edit
            for map_layer in resource.map_layers:
                ows_layer = map_layer.owslayer
                form.sublayers.append_entry({
                    'layer_id': ows_layer.gdi_oid,
                    'layer_name': ows_layer.name,
                    'layer_transparency': map_layer.layer_transparency,
                    'layer_active': map_layer.layer_active,
                    'layer_order': map_layer.layer_order
                })

            if resource.thumbnail_image:
                # set that thumbnail image is present
                form.thumbnail_present = True

            # select background layer
            form.background_layer.data = resource.gdi_oid_default_bg_layer

            # add permissions for resource on edit
            roles = self.PermissionsHelper.resource_roles(resource.gdi_oid)
            for role in roles:
                form.permissions.append_entry({
                    'role_id': role.id,
                    'role_name': role.name,
                    'read': True
                })

        # load related resources from DB
        session = self.session()
        query = session.query(self.BackgroundLayer) \
            .order_by(self.BackgroundLayer.name)
        background_layers = query.all()
        session.close()

        # set choices for responsible select field
        form.responsible.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        # reorder fields by layer_order
        form.sublayers.entries.sort(key=lambda f: int(f.layer_order.data))

        # set choices for map layer select field
        form.layer.choices = self.wms_layer_choices()

        # set choices for background layer select field
        form.background_layer.choices = [(0, "")] + [
            (bg_layer.gdi_oid, bg_layer.name) for bg_layer in background_layers
        ]

        # collect role ids from permissions subform
        role_permission_ids = [
            int(permission.data['role_id']) for permission in form.permissions
        ]

        # set choices for role permission select field
        # skip roles from permissions subform
        roles = self.PermissionsHelper.roles()
        form.role.choices = [
            (role.id, role.name) for role in roles
            if role.id not in role_permission_ids
        ]

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Map records in DB.

        :param object resource: Optional map object
                                (None for create)
        :param FlaskForm form: Form for Map
        :param Session session: DB session
        """
        # get wms_wfs for WMS
        query = session.query(self.WmsWfs).filter_by(ows_type='WMS')
        wms_wfs = query.first()

        if resource is None:
            # create new map
            map_obj = self.Map()
            session.add(map_obj)
        else:
            # update existing map
            map_obj = resource

        # update map
        map_obj.name = form.name.data
        map_obj.description = form.description.data
        if wms_wfs is not None:
            map_obj.gdi_oid_wms_wfs = wms_wfs.gdi_oid
        if form.background_layer.data > 0:
            map_obj.gdi_oid_default_bg_layer = form.background_layer.data
        else:
            map_obj.gdi_oid_default_bg_layer = None
        map_obj.title = form.title.data
        map_obj.initial_extent = form.initial_extent.data
        map_obj.initial_scale = form.initial_scale.data

        if map_obj.map_order is None:
            # set map_order of new map to be at end of map list
            query = session.query(self.Map) \
                .order_by(self.Map.map_order.desc())
            last_map = query.first()
            if last_map:
                map_obj.map_order = last_map.map_order + 1

        # lookup for map_layer of map layers
        resource_map_layers = {}
        for map_layer in map_obj.map_layers:
            ows_layer = map_layer.owslayer
            resource_map_layers[ows_layer.gdi_oid] = map_layer

        # update map_layer
        sub_layer_ids = []
        for sub_layer in form.sublayers:
            layer_id = int(sub_layer.data['layer_id'])
            sub_layer_ids.append(layer_id)
            if layer_id in resource_map_layers:
                # update existing map_layer
                map_layer = resource_map_layers[layer_id]
                map_layer.layer_order = sub_layer.data['layer_order']
                map_layer.layer_active = sub_layer.data['layer_active']
                map_layer.layer_transparency = \
                    sub_layer.data['layer_transparency']
            else:
                # create new map_layer
                new_map_layer = self.MapLayer(
                    gdi_oid_ows_layer=layer_id,
                    layer_order=sub_layer.data['layer_order'],
                    layer_active=sub_layer.data['layer_active'],
                    layer_transparency=sub_layer.data['layer_transparency']
                )
                # add to map
                map_obj.map_layers.append(new_map_layer)

        # remove removed map layers
        for layer_id, map_layer in resource_map_layers.items():
            if map_layer.gdi_oid_ows_layer not in sub_layer_ids:
                # remove map_layer
                map_obj.map_layers.remove(map_layer)
                session.delete(map_layer)

        if form.thumbnail_file.data:
            # save uploaded thumbnail image
            target_filename = (
                str(uuid.uuid4()) +
                os.path.splitext(form.thumbnail_file.data.filename)[1]
            )
            target_path = os.path.join(self.qwc_assets_dir(), target_filename)
            with open(target_path, 'wb') as f:
                f.write(request.files[form.thumbnail_file.name].read())
            map_obj.thumbnail_image = target_filename
        elif form.remove_thumbnail.data:
            thumbnail_path = os.path.join(
                self.qwc_assets_dir(), map_obj.thumbnail_image
            )
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                pass
            map_obj.thumbnail_image = None

        # NOTE: flush object changes in session to update gdi_oid of a new map
        session.flush()

        # update resource contact
        self.ContactsHelper.update_resource_contact(
            map_obj.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE,
            form.responsible.data, session
        )

        # update permissions
        self.update_permissions(map_obj, form, session)

    def destroy_resource(self, resource, session):
        """Delete existing Map records in DB.

        :param object resource: map object
        :param Session session: DB session
        """
        # remove map, resource contact and permissions
        map_obj = resource
        self.ContactsHelper.remove_resource_contacts(
            map_obj.gdi_oid, session
        )
        self.PermissionsHelper.remove_resource_permissions(
            map_obj.gdi_oid, session
        )
        session.delete(map_obj)

    def update_map_order(self):
        """Update map_order in Map records."""
        map_order = request.form.get('map_order')
        if map_order:
            session = self.session()

            # update map_order fields
            map_ids = map_order.split(',')
            for order, map_id in enumerate(map_ids):
                map_obj = self.find_resource(map_id, session)
                if map_obj:
                    map_obj.map_order = order

            # commit changes
            session.commit()
            session.close()

            flash('Reihenfolge der Maps wurde aktualisiert.', 'success')

        return redirect(url_for(self.base_route))

    def wms_layer_choices(self):
        """Return select field choices for all WMS layers."""
        choices = []

        # get WMS root layer
        session = self.session()
        root_layer = self.OWSHelper.find_ows_root_layer('WMS', session)
        if root_layer is not None:
            # recursively collect sub layers
            self.collect_layers(root_layer, choices)
            # remove WMS root layer
            choices.pop(0)
            # remove duplicates
            choices = list(set(choices))
            # order by layer name
            choices.sort(key=lambda c: c[1].lower())

        session.close()

        return choices

    def collect_layers(self, layer, choices):
        """Recursively collect layer info for layer subtree from ConfigDB.

        :param obj layer: Group or Data layer object
        :param list[obj] choices: List of collected layer choices
        """
        # add layer
        choices.append((layer.gdi_oid, layer.name))

        if layer.type == 'group':
            # recursively collect sub layers
            for group_layer in layer.sub_layers:
                self.collect_layers(
                    group_layer.sub_layer, choices
                )

    def update_permissions(self, map_obj, form, session):
        """Add or remove permissions for map.

        :param object map_obj: map object
        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        for permission in form.permissions:
            role_id = permission.data['role_id']
            read = permission.data['read']

            role = self.PermissionsHelper.role(role_id)
            if role is not None:
                # update permissions for map
                self.PermissionsHelper.update_resource_permission(
                    map_obj.gdi_oid, role.id, read, False, session
                )

    def qwc_assets_dir(self):
        """Return target dir for QWC assets."""
        # get dir from service config
        config = self.service_config()
        return config.get('qwc_assets_dir', '/tmp/')
