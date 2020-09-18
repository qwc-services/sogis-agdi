import mimetypes
import os

from flask import flash, json, jsonify, request, Response

from .contacts_helper import ContactsHelper
from .controller import Controller
from .ows_helper import OWSHelper
from forms import ProductSetGUIForm


class ProductSetGUIController(Controller):
    """Controller for ProductSet GUI

    Manage ows_layer_group and related models from combined GUI.
    """

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(ProductSetGUIController, self).__init__(
            "ProductSet", 'product_sets', 'product_set', 'product_set_gui',
            app, config_models
        )
        self.OWSHelper = OWSHelper(config_models)
        self.ContactsHelper = ContactsHelper(config_models, app.logger)

        self.OWSLayerGroup = self.config_models.model('ows_layer_group')
        self.OWSLayer = self.config_models.model('ows_layer')
        self.GroupLayer = self.config_models.model('group_layer')
        self.TemplateInfo = self.config_models.model('template_info')
        self.TemplateJasper = self.config_models.model('template_jasper')

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # download legend image
        app.add_url_rule(
            '/%s/<int:id>/legend/<string:filename>' % base_route,
            '%s_legend' % suffix, self.download_legend, methods=['GET']
        )

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return ProductSet list.

        :param Session session: DB session
        """
        return session.query(self.OWSLayerGroup) \
            .order_by(self.OWSLayerGroup.name).all()

    def form_for_new(self):
        """Return form for new ProductSet."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating ProductSet."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new ProductSet records in DB.

        :param FlaskForm form: Form for ProductSet
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find ProductSet by ows_layer_group ID.

        :param int id: ows_layer_group ID
        :param Session session: DB session
        """
        return session.query(self.OWSLayerGroup).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing ProductSet.

        :param object resource: ows_layer_group object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating ProductSet.

        :param object resource: ows_layer_group object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing ProductSet records in DB.

        :param object resource: ows_layer_group object
        :param FlaskForm form: Form for ProductSet
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional ows_layer_group object
        :param bool edit_form: Set if edit form
        """
        form = ProductSetGUIForm(self.config_models, obj=resource)

        # load related resources from DB
        session = self.session()

        query = session.query(self.OWSLayer).order_by(self.OWSLayer.name)
        if resource is not None:
            # skip resource itself
            query = query.filter(self.OWSLayer.gdi_oid != resource.gdi_oid)

        # skip WMS root layers
        root_layers = self.OWSHelper.ows_root_layers(session)
        root_layer_ids = [l.gdi_oid for l in root_layers]
        if root_layer_ids:
            query = query.filter(~self.OWSLayer.gdi_oid.in_(root_layer_ids))

        layers = query.all()

        session.close()

        if edit_form:
            # override form fields with resource values on edit

            if resource.ows_metadata:
                try:
                    # load JSON from ows_metadata
                    ows_metadata = json.loads(resource.ows_metadata)

                    # update abstract on edit
                    form.abstract.data = ows_metadata.get('abstract')
                except ValueError as e:
                    msg = (
                        "Ungültiges JSON in "
                        "ows_layer.ows_metadata: %s" % e
                    )
                    self.logger.error(msg)
                    flash(msg, 'error')

            # data owner
            form.data_owner.data = self.ContactsHelper.resource_contact_id(
                resource.gdi_oid, self.ContactsHelper.ROLE_DATA_OWNER
            )

            # add sub layers for resource on edit
            for group_layer in resource.sub_layers:
                sub_layer = group_layer.sub_layer
                form.sublayers.append_entry({
                    'layer_id': sub_layer.gdi_oid,
                    'layer_name': sub_layer.name,
                    'layer_active': group_layer.layer_active,
                    'layer_order': group_layer.layer_order
                })

            # update WMS checkbox on edit
            form.in_wms.data = self.OWSHelper.layer_in_ows(resource, 'WMS')
            # update WFS checkbox on edit
            form.in_wfs.data = self.OWSHelper.layer_in_ows(resource, 'WFS')

            # facade
            form.facade.data = resource.facade

            if resource.legend_image:
                # show whether legend image is present
                form.legend_present = True
                form.legend_file.description = 'Legende vorhanden'

                if resource.legend_filename:
                    # add download link for uploaded legend
                    filename = os.path.basename(resource.legend_filename)
                    form.legend_file.description = (
                        'Legende vorhanden: '
                        '<a href="legend/%s" target="_blank">%s</a>' %
                        (filename, filename)
                    )

        # set choices for data owner select field
        form.data_owner.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        # reorder fields by layer_order
        form.sublayers.entries.sort(key=lambda x: int(x.layer_order.data))

        # set choices for sub layer select field
        form.layer.choices = [(layer.gdi_oid, layer.name) for layer in layers]

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update ProductSet records in DB.

        :param object resource: Optional ows_layer_group object
                                (None for create)
        :param FlaskForm form: Form for ProductSet
        :param Session session: DB session
        """
        if resource is None:
            # create new ows_layer_group
            ows_layer_group = self.OWSLayerGroup()
            session.add(ows_layer_group)
        else:
            # update existing ows_layer_group
            ows_layer_group = resource

        # update ows_layer_group
        ows_layer_group.name = form.name.data
        ows_layer_group.description = form.description.data
        ows_layer_group.title = form.title.data
        ows_layer_group.facade = form.facade.data
        ows_layer_group.synonyms = form.synonyms.data
        ows_layer_group.keywords = form.keywords.data

        # update metadata
        if form.abstract.data:
            # create JSON from form data
            ows_metadata = json.dumps({
                'abstract': form.abstract.data,
            }, ensure_ascii=False, indent=2)

            ows_layer_group.ows_metadata = ows_metadata
        else:
            ows_layer_group.ows_metadata = None

        if form.facade.data and form.legend_file.data:
            # save uploaded legend image
            legend_data = request.files[form.legend_file.name].read()
            ows_layer_group.legend_image = legend_data
            ows_layer_group.legend_filename = form.legend_file.data.filename
        elif form.remove_legend.data:
            # remove existing legend image
            ows_layer_group.legend_image = None
            ows_layer_group.legend_filename = None

        # lookup for group_layer of sub layers
        resource_sub_layers = {}
        for group_layer in ows_layer_group.sub_layers:
            sub_layer = group_layer.sub_layer
            resource_sub_layers[sub_layer.gdi_oid] = group_layer

        # update group_layer
        sub_layer_ids = []
        for sub_layer in form.sublayers:
            layer_id = int(sub_layer.data['layer_id'])
            sub_layer_ids.append(layer_id)
            if layer_id in resource_sub_layers:
                # update existing group_layer
                group_layer = resource_sub_layers[layer_id]
                group_layer.layer_active = sub_layer.data['layer_active']
                group_layer.layer_order = sub_layer.data['layer_order']
            else:
                # create new group_layer
                new_group_layer = self.GroupLayer(
                    gdi_oid_sub_layer=layer_id,
                    layer_active=sub_layer.data['layer_active'],
                    layer_order=sub_layer.data['layer_order']
                )
                # add to ows_layer_group
                ows_layer_group.sub_layers.append(new_group_layer)

        # remove removed sub layers
        for layer_id, group_layer in resource_sub_layers.items():
            if group_layer.gdi_oid_sub_layer not in sub_layer_ids:
                # remove group_layer
                ows_layer_group.sub_layers.remove(group_layer)
                session.delete(group_layer)

        # update WMS/WFS
        self.OWSHelper.update_ows(
            ows_layer_group, 'WMS', form.in_wms.data, session
        )
        self.OWSHelper.update_ows(
            ows_layer_group, 'WFS', form.in_wfs.data, session
        )

        # update resource contact
        self.ContactsHelper.update_resource_contact(
            ows_layer_group.gdi_oid, self.ContactsHelper.ROLE_DATA_OWNER,
            form.data_owner.data, session
        )

    def destroy_resource(self, resource, session):
        """Delete existing ProductSet records in DB.

        :param object resource: ows_layer_group object
        :param Session session: DB session
        """
        ows_layer_group = resource

        # remove OWS layer from WMS/WFS
        self.OWSHelper.update_ows(ows_layer_group, 'WMS', False, session)
        self.OWSHelper.update_ows(ows_layer_group, 'WFS', False, session)

        # remove resource contact
        self.ContactsHelper.remove_resource_contacts(
            ows_layer_group.gdi_oid, session
        )

        # remove ows_layer_group and associated resources
        session.delete(ows_layer_group)

    def download_legend(self, id, filename):
        """Download uploaded legend image.

        :param int id: ows_layer_group ID
        :param string filename: File name of uploaded legend
                                (only for route, ignored otherwise)
        """
        # find ows_layer_group
        session = self.session()
        ows_layer_group = self.find_resource(id, session)
        session.close()

        if ows_layer_group is not None and ows_layer_group.legend_filename:
            # guess content type from filename
            filename = ows_layer_group.legend_filename
            content_type = mimetypes.guess_type(filename)[0] \
                or 'application/octet-stream'
            # return uploaded legend image with original filename
            return Response(
                ows_layer_group.legend_image,
                content_type=content_type,
                headers={
                    'content-disposition': 'attachment; filename=%s' % filename
                },
                status=200
            )

        # ows_layer_group not found or no legend present
        abort(404)
