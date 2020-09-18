from flask import json
from flask import request
import os
import uuid

from .controller import Controller
from .permissions_helper import PermissionsHelper
from forms import BackgroundLayerForm


class BackgroundLayersController(Controller):
    """Controller for BackgroundLayer GUI

    Manage background_layer from GUI.
    """

    def __init__(self, app, config_models, service_config):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param func service_config: Helper method for reading service config
        """
        super(BackgroundLayersController, self).__init__(
            "BackgroundLayer", 'background_layers', 'background_layer',
            'background_layers', app, config_models
        )
        self.service_config = service_config
        self.PermissionsHelper = PermissionsHelper(config_models)
        self.BackgroundLayer = self.config_models.model('background_layer')

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return background layers list.

        :param Session session: DB session
        """
        return session.query(self.BackgroundLayer) \
            .order_by(self.BackgroundLayer.name).all()

    def form_for_new(self):
        """Return form for new background layer."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating BackgroundLayer."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new BackgroundLayer records in DB.

        :param FlaskForm form: Form for BackgroundLayer
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find BackgroundLayer by ID.

        :param int id: BackgroundLayer ID
        :param Session session: DB session
        """
        return session.query(self.BackgroundLayer) \
            .filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing BackgroundLayer.

        :param object resource: BackgroundLayer object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating BackgroundLayer.

        :param object resource: background_layer object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing BackgroundLayer records in DB.

        :param object resource: background_layer object
        :param FlaskForm form: Form for BackgroundLayer
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional background_layer object
        :param bool edit_form: Set if edit form
        """
        form = BackgroundLayerForm(self.config_models, obj=resource)

        if edit_form:
            if resource.thumbnail_image:
                # set that thumbnail image is present
                form.thumbnail_present = True

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update BackgroundLayer records in DB.

        :param object resource: Optional background_layer object
                                (None for create)
        :param FlaskForm form: Form for BackgroundLayer
        :param Session session: DB session
        """
        if resource is None:
            # create new background_layer
            background_layer = self.BackgroundLayer()
            session.add(background_layer)
        else:
            # update existing background_layer
            background_layer = resource

        # update background_layer
        background_layer.name = form.name.data
        background_layer.description = form.description.data
        background_layer.qgis_datasource = form.qgis_datasource.data
        background_layer.qwc2_bg_layer_config = form.qwc2_bg_layer_config.data

        # get QWC2 background layer name from config
        qwc2_config = json.loads(background_layer.qwc2_bg_layer_config)
        background_layer.qwc2_bg_layer_name = qwc2_config.get('name', '')

        if form.thumbnail_file.data:
            # save uploaded thumbnail image
            target_filename = (
                str(uuid.uuid4()) +
                os.path.splitext(form.thumbnail_file.data.filename)[1]
            )
            target_path = os.path.join(self.qwc_assets_dir(), target_filename)
            with open(target_path, 'wb') as f:
                f.write(request.files[form.thumbnail_file.name].read())
            background_layer.thumbnail_image = target_filename
        elif form.remove_thumbnail.data:
            thumbnail_path = os.path.join(
                self.qwc_assets_dir(), background_layer.thumbnail_image
            )
            try:
                os.remove(thumbnail_path)
            except Exception as e:
                pass
            background_layer.thumbnail_image = None

        # NOTE: flush object changes in session to update gdi_oid of a
        #       new background_layer
        session.flush()

        # add default public permission
        role = self.PermissionsHelper.public_role()
        if role is not None:
            self.PermissionsHelper.update_resource_permission(
                background_layer.gdi_oid, role.id, True, False, session
            )

    def destroy_resource(self, resource, session):
        """Delete existing BackgroundLayer records in DB.

        :param object resource: background_layer object
        :param Session session: DB session
        """
        # remove background_layer and permissions
        background_layer = resource
        self.PermissionsHelper.remove_resource_permissions(
            background_layer.gdi_oid, session
        )
        session.delete(background_layer)

    def qwc_assets_dir(self):
        """Return target dir for QWC assets."""
        # get dir from service config
        config = self.service_config()
        return config.get('qwc_assets_dir', '/tmp/')
