from collections import OrderedDict
import hashlib
import mimetypes
import os
import re
import uuid
import zipfile
from xml.etree import ElementTree

from flask import abort, flash, json, jsonify, request, Response, \
    send_from_directory
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import text as sql_text

from .contacts_helper import ContactsHelper
from .controller import Controller
from .ows_helper import OWSHelper
from .permissions_helper import PermissionsHelper
from forms import DataSetGUIForm


class DataSetGUIController(Controller):
    """Controller for DataSet GUI

    Manage data_set_view and related models from combined GUI.
    """

    # subdir for QGS symbols relative to PROJECT_OUTPUT_DIR
    SYMBOLS_SUB_DIR = 'symbols'

    # subdir for uploaded files relative to PROJECT_OUTPUT_DIR
    UPLOADS_SUB_DIR = 'uploads'

    def __init__(self, app, config_models, db_engine, service_config):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param DatabaseEngine db_engine: Database engine with DB connections
        :param func service_config: Helper method for reading service config
        """
        super(DataSetGUIController, self).__init__(
            "DataSet", 'data_sets', 'data_set', 'data_set_gui', app,
            config_models
        )
        self.db_engine = db_engine
        self.service_config = service_config
        self.OWSHelper = OWSHelper(config_models)
        self.ContactsHelper = ContactsHelper(config_models, app.logger)
        self.PermissionsHelper = PermissionsHelper(config_models)

        self.DataSetView = self.config_models.model('data_set_view')
        self.DataSet = self.config_models.model('data_set')
        self.DataSource = self.config_models.model('data_source')
        self.Attribute = self.config_models.model('data_set_view_attributes')
        self.OWSLayerData = self.config_models.model('ows_layer_data')
        self.DataSetEdit = self.config_models.model('data_set_edit')
        self.TemplateInfo = self.config_models.model('template_info')
        self.TemplateJasper = self.config_models.model('template_jasper')

        self.Role = self.config_models.model('role')
        self.ResourcePermission = self.config_models.model(
            'resource_permission'
        )

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # tables lookup
        app.add_url_rule(
            '/%s/tables' % base_route,
            '%s_tables' % suffix, self.data_source_tables, methods=['GET']
        )
        # table metadata lookup
        app.add_url_rule(
            '/%s/metadata' % base_route,
            '%s_metadata' % suffix, self.metadata, methods=['GET']
        )
        # rasters lookup
        app.add_url_rule(
            '/%s/rasters' % base_route,
            '%s_rasters' % suffix, self.data_source_rasters, methods=['GET']
        )
        # JSON attributes lookup
        app.add_url_rule(
            '/%s/json_attrs' % base_route,
            '%s_json_attrs' % suffix, self.json_attributes, methods=['GET']
        )
        # download legend image
        app.add_url_rule(
            '/%s/<int:id>/legend/<string:filename>' % base_route,
            '%s_legend' % suffix, self.download_legend, methods=['GET']
        )
        # download uploaded QML file
        app.add_url_rule(
            '/%s/<int:id>/qml/<string:filename>' % base_route,
            '%s_gml' % suffix, self.download_qml, methods=['GET']
        )
        app.add_url_rule(
            '/%s/<int:id>/client_qml/<string:filename>' % base_route,
            '%s_client_gml' % suffix, self.download_client_qml, methods=['GET']
        )

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return DataSet list.

        :param Session session: DB session
        """
        query = session.query(self.DataSetView).order_by(self.DataSetView.name)
        # eager load relations
        query = query.options(joinedload(self.DataSetView.ows_layers))
        query = query.options(joinedload(self.DataSetView.data_set))

        return query.all()

    def form_for_new(self):
        """Return form for new DataSet."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating DataSet."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new DataSet records in DB.

        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find DataSet by data_set_view ID.

        :param int id: data_set_view ID
        :param Session session: DB session
        """
        query = session.query(self.DataSetView).filter_by(gdi_oid=id)
        # eager load relations
        query = query.options(joinedload(self.DataSetView.attributes))

        return query.first()

    def form_for_edit(self, resource):
        """Return form for editing DataSet.

        :param object resource: data_set_view object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating DataSet.

        :param object resource: data_set_view object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing DataSet records in DB.

        :param object resource: data_set_view object
        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional data_set_view object
        :param bool edit_form: Set if edit form
        """
        form = DataSetGUIForm(self.config_models, obj=resource)
        if resource is not None:
            # select DataSet type
            form.connection_type.data = resource.data_set.data_source \
                .connection_type
            if resource.data_set.data_source.connection_type in (
                    'wms', 'wmts'):
                form.connection_type.data = 'ows'
            if not resource.ows_layers:
                # basic data set if no ows_layer_data present
                form.connection_type.data = 'basic_database'

        if edit_form:
            # override form fields with resource values on edit
            # select options for resource

            # data owner
            form.data_owner.data = self.ContactsHelper.resource_contact_id(
                resource.gdi_oid, self.ContactsHelper.ROLE_DATA_OWNER
            )

            # vector
            form.data_source.data = resource.data_set.gdi_oid_data_source
            form.db_table.data = resource.data_set.data_set_name
            form.geom_column.data = resource.geometry_column
            form.primary_key.data = resource.data_set.primary_key

            # raster
            form.raster_data_source.data = resource.data_set.gdi_oid_data_source
            form.raster_data_set.data = resource.data_set.data_set_name

            # basic data set
            form.basic_data_source.data = resource.data_set.gdi_oid_data_source
            form.basic_db_table.data = resource.data_set.data_set_name

            # ows data set
            form.ows_data_source.data = resource.data_set.gdi_oid_data_source
            form.ows_service_layers.data = resource.data_set.data_set_name
        else:
            # set default transparency
            if form.transparency.data is None:
                form.transparency.data = 0

        # load related resources from DB
        session = self.session()

        ds_query = session.query(self.DataSource).order_by(self.DataSource.name)
        data_sources = ds_query.filter_by(connection_type='database').all()
        raster_sources = ds_query.filter_by(connection_type='directory').all()
        ows_sources = ds_query.filter(
            self.DataSource.connection_type.in_(['wms', 'wmts'])).all()

        info_html_query = session.query(self.TemplateInfo) \
            .order_by(self.TemplateInfo.name)
        info_templates = info_html_query.all()

        object_sheet_query = session.query(self.TemplateJasper) \
            .order_by(self.TemplateJasper.name)
        object_sheets = object_sheet_query.all()

        roles_query = session.query(self.Role).order_by(self.Role.name)
        roles = roles_query.all()

        session.close()

        # set choices for data owner select field
        form.data_owner.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        # set choices for data source select field (PostGIS data sources)
        postgis_data_sources = self.postgis_data_source_choices(data_sources)
        form.data_source.choices = [(0, "")] + postgis_data_sources

        # set choices for raster data source select field
        form.raster_data_source.choices = [(0, "")] + [
            (ds.gdi_oid, ds.name) for ds in raster_sources
        ]

        # set choices for ows data source select field
        form.ows_data_source.choices = [(0, "")] + [
            (ds.gdi_oid, ds.name) for ds in ows_sources
        ]

        # set choices for basic data source select field (all DB data sources)
        form.basic_data_source.choices = [(0, "")] + [
            (ds.gdi_oid, ds.name) for ds in data_sources
        ]

        is_vector_data_set = (form.connection_type.data == 'database')
        is_raster_data_set = (form.connection_type.data == 'directory')
        is_basic_data_set = (form.connection_type.data == 'basic_database')
        is_ows_data_set = (form.connection_type.data == 'ows')
        if is_vector_data_set and form.data_source.data and \
                form.data_source.data > 0:
            # vector DataSet

            tables = []
            metadata = None

            # load tables from GeoDB
            postgis_tables = self.postgis_tables(form.data_source.data)
            if 'error' not in postgis_tables:
                tables = postgis_tables.get('tables', [])
                # set choices for table select field
                form.db_table.choices = [("", "")] + [
                    (table, table) for table in tables
                ]

                # load table metadata
                metadata = self.dataset_info(
                    form.data_source.data, form.db_table.data
                )
                if metadata is not None and 'error' in metadata:
                    # show metadata error
                    form.db_alert_title = \
                        "Fehler beim Laden der Tabellen-Metadaten:"
                    form.db_alert_msg = metadata.get('error')
                    metadata = None
            else:
                # show tables error
                form.db_alert_title = "Fehler beim Laden der Tabellen:"
                form.db_alert_msg = postgis_tables.get('error')

            # toggle primary key field
            form.primary_key_required = False
            if metadata is not None and metadata['primary_key'] is None:
                form.primary_key_required = True

            # set choices for geometry column select field
            form.geom_column.choices = []
            if metadata is not None and len(metadata['geometry_columns']) > 1:
                for geom_column in metadata['geometry_columns']:
                    geometry_column = geom_column['geometry_column']
                    geometry_type = geom_column['geometry_type']
                    label = "%s (%s)" % (geometry_column, geometry_type)
                    form.geom_column.choices.append((geometry_column, label))

            # NOTE: attribute subform will be filled from submitted form data,
            #       except for edit form
            if edit_form:
                # add attributes for resource on edit
                self.add_form_attributes(resource, form, metadata)

        elif is_raster_data_set and form.raster_data_source.data and \
                form.raster_data_source.data > 0:
            # raster DataSet

            # load raster files from directory
            rasters = self.raster_files(form.raster_data_source.data)

            # set choices for raster select field
            form.raster_data_set.choices = [("", "")] + [
                (raster, raster) for raster in rasters
            ]

        # set choices for info template select field
        form.info_template.choices = [(0, "kein spezieller Infobutton")] + [
            (t.gdi_oid, t.name) for t in info_templates
        ]

        # set choices for object sheet select field
        form.object_sheet.choices = [(0, "kein Objektblatt")] + [
            (o.gdi_oid, o.name) for o in object_sheets
        ]

        if resource is not None:
            # get associated ows_layer_data
            ows_layers = resource.ows_layers
            if ows_layers:
                ows_layer = ows_layers[0]
                if edit_form:
                    # update title on edit
                    form.title.data = ows_layer.title

                    # update Solr fields
                    form.synonyms.data = ows_layer.synonyms
                    form.keywords.data = ows_layer.keywords

                    if ows_layer.ows_metadata:
                        try:
                            # load JSON from ows_metadata
                            ows_metadata = json.loads(ows_layer.ows_metadata)

                            # update abstract on edit
                            form.abstract.data = ows_metadata.get('abstract')
                        except ValueError as e:
                            msg = (
                                "Ungültiges JSON in "
                                "ows_layer.ows_metadata: %s" % e
                            )
                            self.logger.error(msg)
                            flash(msg, 'error')

                    # update transparency on edit
                    form.transparency.data = ows_layer.layer_transparency

                    # update WMS checkbox on edit
                    form.in_wms.data = self.OWSHelper.layer_in_ows(
                        ows_layer, 'WMS'
                    )
                    if is_vector_data_set:
                        # update WFS checkbox on edit
                        form.in_wfs.data = self.OWSHelper.layer_in_ows(
                            ows_layer, 'WFS'
                        )

                    # update info template on edit
                    form.info_template.data = ows_layer.gdi_oid_info_template
                    # update object sheet on edit
                    form.object_sheet.data = ows_layer.gdi_oid_object_sheet
                if ows_layer.legend_image:
                    # show whether legend image is present
                    form.legend_present = True
                    form.legend_file.description = 'Legende vorhanden'

                    if ows_layer.legend_filename:
                        # add download link for uploaded legend
                        filename = os.path.basename(ows_layer.legend_filename)
                        form.legend_file.description = (
                            'Legende vorhanden: '
                            '<a href="legend/%s" target="_blank">%s</a>' %
                            (filename, filename)
                        )

                if ows_layer.qgs_style:
                    # show whether layer style is present
                    form.qml_present = True
                    form.qml_file.description = 'QML vorhanden'

                    if ows_layer.uploaded_qml:
                        # add download link for uploaded QML
                        filename = os.path.basename(ows_layer.uploaded_qml)
                        form.qml_file.description = (
                            'QML vorhanden: '
                            '<a href="qml/%s" target="_blank">%s</a>' %
                            (filename, filename)
                        )

                if ows_layer.client_qgs_style:
                    # show whether client layer style is present
                    form.client_qml_present = True
                    form.client_qml_file.description = 'QML vorhanden'

                    if ows_layer.uploaded_client_qml:
                        # add download link for uploaded client QML
                        filename = os.path.basename(
                            ows_layer.uploaded_client_qml
                        )
                        form.client_qml_file.description = (
                            'QML vorhanden: '
                            '<a href="client_qml/%s" target="_blank">%s</a>' %
                            (filename, filename)
                        )

        # reorder fields by attr_order
        form.attrs.entries.sort(key=lambda x: int(x.form.attr_order.data))

        if edit_form:
            # add permissions for resource on edit
            self.add_form_permissions(resource, form)

        # collect role ids from permissions subform
        role_permission_ids = [
            int(permission.data['role_id']) for permission in form.permissions
        ]

        # set choices for role permission select field
        # skip roles from permissions subform
        form.role.choices = [
            (role.id, role.name) for role in roles
            if role.id not in role_permission_ids
        ]

        return form

    def add_form_attributes(self, resource, form, metadata):
        """Add attributes subform for resource.

        :param object resource: data_set_view object
        :param FlaskForm form: Form for DataSet
        :param object metadata: Table metadata for data_set
        """
        if metadata is None:
            # could not load metadata
            return

        # add attribute subform entries from resource
        attr_index = 0
        for resource_attr in resource.attributes:
            if resource_attr.name in metadata['attributes']:
                # get any JSON attributes from alias data
                alias = resource_attr.alias
                json_attrs = []
                try:
                    if alias.startswith('{'):
                        # parse JSON
                        json_config = json.loads(alias)
                        alias = json_config.get('alias', alias)
                        json_attrs = json_config.get('json_attrs', [])
                except Exception as e:
                    self.logger.warning(
                        "Could not parse value as JSON: '%s'\n%s" %
                        (resource_attr.alias, e)
                    )

                form.attrs.append_entry({
                    'name': resource_attr.name,
                    'alias': alias,
                    'format': resource_attr.format,
                    'active': True,
                    'displayfield': resource_attr.displayfield,
                    'attr_order': attr_index,
                    'json_attrs': json_attrs,
                })

                attr_index += 1

        # lookup for resource attributes
        resource_attrs = {}
        for attr in resource.attributes:
            resource_attrs[attr.name] = attr

        # add remaining attribute subform entries from metadata
        for attr in metadata['attributes']:
            if attr not in resource_attrs:
                form.attrs.append_entry({
                    'name': attr,
                    'attr_order': attr_index
                })

                attr_index += 1

    def add_form_permissions(self, resource, form):
        """Add permissions subform for resource.

        NOTE: Read permissions for data_set_view only.
              All related resources have identical permissions.

        :param object resource: data_set_view object
        :param FlaskForm form: Form for DataSet
        """
        # get permitted roles for data_set_view from DB
        session = self.session()
        query = session.query(self.Role) \
            .join(self.Role.resource_permission_collection) \
            .filter(
                self.ResourcePermission.gdi_oid_resource == resource.gdi_oid
            ) \
            .order_by(self.Role.name)
        roles = query.all()

        edit_config = self.get_edit_config(resource)

        # add permission subform entries
        for role in roles:
            writable = False
            if edit_config:
                # get writable permission for role and edit config from DB
                query = session.query(self.ResourcePermission) \
                    .join(self.ResourcePermission.role) \
                    .filter(self.ResourcePermission.id_role == role.id) \
                    .filter(self.ResourcePermission.gdi_oid_resource ==
                            edit_config.gdi_oid) \
                    .filter(self.ResourcePermission.write)
                permission = query.first()
                writable = (permission is not None)

            form.permissions.append_entry({
                'role_id': role.id,
                'role_name': role.name,
                'read': True,
                'write': writable
            })

        session.close()

    def create_or_update_resources(self, resource, form, session):
        """Create or update DataSet records in DB.

        :param object resource: Optional data_set_view object (None for create)
        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        is_vector_data_set = (form.connection_type.data == 'database')
        is_raster_data_set = (form.connection_type.data == 'directory')
        is_basic_data_set = (form.connection_type.data == 'basic_database')
        is_ows_data_set = (form.connection_type.data == 'ows')

        if resource is None:
            # create new data_set_view
            data_set_view = self.DataSetView()
            session.add(data_set_view)
            # create new data_set
            data_set = self.DataSet()
            data_set_view.data_set = data_set
            session.add(data_set)
        else:
            # update existing data_set_view
            data_set_view = resource

        if (
            not is_basic_data_set
            and (not form.title.data or form.title.data == 'None')
        ):
            self.raise_validation_error(
                form.title, "Titel darf nicht leer sein"
            )

        # update data_set_view
        data_set_view.name = form.name.data
        data_set_view.description = form.description.data
        if is_vector_data_set:
            # NOTE: optional geom_column returns 'None' as string if not set
            if form.geom_column.data != 'None':
                data_set_view.geometry_column = form.geom_column.data
            else:
                data_set_view.geometry_column = None
        data_set_view.feature_id_column = form.feature_id_column.data
        data_set_view.facet = form.facet.data
        data_set_view.filter_word = form.filter_word.data
        data_set_view.searchable = form.searchable.data

        # update data_set
        data_set = data_set_view.data_set
        data_set.name = form.name.data
        data_set.description = form.description.data
        if is_vector_data_set:
            # vector DataSet

            # require vector data_source and data_set
            if form.data_source.data == 0:
                self.raise_validation_error(
                    form.data_source, "Keine DataSource ausgewählt"
                )
            if not form.db_table.data or form.db_table.data == 'None':
                self.raise_validation_error(
                    form.db_table, "Keine DB Entität ausgewählt"
                )

            data_set.data_set_name = form.db_table.data
            data_set.gdi_oid_data_source = form.data_source.data

            # load table metadata
            metadata = self.dataset_info(
                form.data_source.data, form.db_table.data
            )
            if metadata is not None and 'error' not in metadata:
                # validate primary key
                if metadata.get('primary_key') is None:
                    if not form.primary_key.data:
                        self.raise_validation_error(
                            form.primary_key,
                            "Primary Key darf nicht leer sein"
                        )
                    elif (
                        form.primary_key.data not in metadata.get('attributes')
                    ):
                        self.raise_validation_error(
                            form.primary_key, "Ungültiger Primary Key"
                        )

            # update primary key
            if form.primary_key.data:
                data_set.primary_key = form.primary_key.data
            else:
                data_set.primary_key = None

            # lookup for resource attributes
            resource_attrs = {}
            for attr in data_set_view.attributes:
                resource_attrs[attr.name] = attr

            db_attrs = set(resource_attrs.keys())
            form_attrs = set()

            # update data_set_view_attributes
            # reorder fields by attr_order
            form.attrs.entries.sort(key=lambda x: int(x.form.attr_order.data))
            # NOTE: attribute order in order of attr_order and
            #       active form attributes
            attr_index = 0
            for attr in form.attrs:
                alias = attr.data['alias']
                # collect JSON attributes
                if attr.form.json_attrs.entries:
                    json_fields = []
                    json_active = False
                    for json_attr in attr.form.json_attrs:
                        json_fields.append({
                            'name': json_attr.data['name'],
                            'alias': json_attr.data['alias'],
                            'active': json_attr.data['active']
                        })
                        json_active |= json_attr.data['active']

                    if json_active:
                        # store JSON attributes as JSON in alias data
                        alias = json.dumps({
                            'alias': alias,
                            'json_attrs': json_fields
                        }, ensure_ascii=False, indent=2)

                form_attrs.add(attr.data['name'])
                if attr.data['name'] in resource_attrs:
                    resource_attr = resource_attrs[attr.data['name']]
                    if attr.data['active']:
                        # update existing attribute
                        resource_attr.alias = alias
                        resource_attr.format = attr.data['format']
                        resource_attr.displayfield = attr.data['displayfield']
                        resource_attr.attribute_order = attr_index

                        attr_index += 1
                    else:
                        # remove existing attribute and its permissions
                        self.PermissionsHelper.remove_resource_permissions(
                            resource_attr.gdi_oid, session
                        )
                        data_set_view.attributes.remove(resource_attr)
                        session.delete(resource_attr)
                elif attr.data['active']:
                    # create new attribute
                    new_attr = self.Attribute(
                        name=attr.data['name'],
                        description="-",
                        alias=alias,
                        format=attr.data['format'],
                        displayfield=attr.data['displayfield'],
                        attribute_order=attr_index
                    )
                    # add to data_set_view
                    data_set_view.attributes.append(new_attr)

                    attr_index += 1

            # Find and remove orphan attributes (attributes in DB but not in form)
            orphan_attrs = db_attrs - form_attrs
            for attr_name in orphan_attrs:
                resource_attr = resource_attrs[attr_name]
                # remove existing attribute and its permissions
                self.PermissionsHelper.remove_resource_permissions(
                    resource_attr.gdi_oid, session
                )
                data_set_view.attributes.remove(resource_attr)
                session.delete(resource_attr)

            # check for any permissions
            has_permissions = False
            for permission in form.permissions:
                if permission.data['read'] or permission.data['write']:
                    has_permissions = True
                    break

            edit_config = self.get_edit_config(data_set_view)
            if edit_config is None:
                # create new edit config
                edit_config = self.DataSetEdit()
                edit_config.data_set_view = data_set_view
                session.add(edit_config)

                # update edit config
                edit_config.name = form.name.data
                edit_config.description = form.description.data
            else:
                if has_permissions:
                    # update existing edit config
                    edit_config.name = form.name.data
                    edit_config.description = form.description.data
                else:
                    # remove existing edit config and its permissions
                    self.PermissionsHelper.remove_resource_permissions(
                        edit_config.gdi_oid, session
                    )
                    data_set_view.data_set_edit_collection.remove(edit_config)
                    session.delete(edit_config)
        elif is_raster_data_set:
            # raster DataSet

            # require raster data_source and data_set
            if form.raster_data_source.data == 0:
                self.raise_validation_error(
                    form.raster_data_source, "Keine DataSource ausgewählt"
                )
            if not form.raster_data_set.data or \
                    form.raster_data_set.data == 'None':
                self.raise_validation_error(
                    form.raster_data_set, "Kein Rasterlayer ausgewählt"
                )

            data_set.data_set_name = form.raster_data_set.data
            data_set.gdi_oid_data_source = form.raster_data_source.data
        elif is_ows_data_set:
            # OWS DataSet

            # require data_source and layers
            if form.ows_data_source.data == 0:
                self.raise_validation_error(
                    form.ows_data_source, "Keine DataSource ausgewählt"
                )
            if not form.ows_service_layers.data or \
                    form.ows_service_layers.data == 'None':
                self.raise_validation_error(
                    form.ows_service_layers, "Kein OWS layer ausgewählt"
                )

            data_set.data_set_name = form.ows_service_layers.data
            data_set.gdi_oid_data_source = form.ows_data_source.data
        else:
            # basic DataSet

            # require vector data_source and data_set
            if form.basic_data_source.data == 0:
                self.raise_validation_error(
                    form.basic_data_source, "Keine DataSource ausgewählt"
                )
            if not form.basic_db_table.data or \
                    form.basic_db_table.data == 'None':
                self.raise_validation_error(
                    form.basic_db_table, "Keine DB Entität ausgewählt"
                )

            data_set.data_set_name = form.basic_db_table.data
            data_set.gdi_oid_data_source = form.basic_data_source.data

            # update resource contacts for GDI resources
            for resource in [data_set, data_set_view]:
                self.ContactsHelper.update_resource_contact(
                    resource.gdi_oid, self.ContactsHelper.ROLE_DATA_OWNER,
                    form.data_owner.data, session
                )

            # NOTE: basic DataSet includes only data_set, dummy data_set_view
            #       and resource_contacts
            # skip vector and raster resources
            return

        # create or get ows_layer_data
        ows_layers = data_set_view.ows_layers
        if not ows_layers:
            # create new ows_layer_data
            ows_layer_data = self.OWSLayerData()
            # assign to data_set_view
            ows_layer_data.data_set_view = data_set_view
            # empty style
            ows_layer_data.qgs_style = ""
        else:
            # update existing ows_layer_data
            ows_layer_data = ows_layers[0]

        # update ows_layer_data
        ows_layer_data.name = form.name.data
        ows_layer_data.description = form.description.data
        ows_layer_data.title = form.title.data
        if form.transparency.data:
            ows_layer_data.layer_transparency = form.transparency.data
        else:
            ows_layer_data.layer_transparency = 0
        ows_layer_data.synonyms = form.synonyms.data
        ows_layer_data.keywords = form.keywords.data

        # update metadata
        if form.abstract.data:
            # create JSON from form data
            ows_metadata = json.dumps({
                'abstract': form.abstract.data,
            }, ensure_ascii=False, indent=2)

            ows_layer_data.ows_metadata = ows_metadata
        else:
            ows_layer_data.ows_metadata = None

        # update info HTML
        if form.info_template.data > 0:
            ows_layer_data.gdi_oid_info_template = form.info_template.data
        else:
            ows_layer_data.gdi_oid_info_template = None

        # update object sheet
        if form.object_sheet.data > 0:
            ows_layer_data.gdi_oid_object_sheet = form.object_sheet.data
        else:
            ows_layer_data.gdi_oid_object_sheet = None

        if form.legend_file.data:
            # save uploaded legend image
            legend_data = request.files[form.legend_file.name].read()
            ows_layer_data.legend_image = legend_data
            ows_layer_data.legend_filename = form.legend_file.data.filename
        elif form.remove_legend.data:
            # remove existing legend image
            ows_layer_data.legend_image = None
            ows_layer_data.legend_filename = None
        if form.qml_file.data:
            # save uploaded QML and symbols
            self.save_qgs_style(ows_layer_data, form)
        elif form.remove_qml.data:
            # remove existing symbols
            self.cleanup_qgs_style_symbols(ows_layer_data.qgs_style)
            ows_layer_data.qgs_style = ""
            # remove uploaded QML
            self.cleanup_uploaded_qml(ows_layer_data)
            ows_layer_data.uploaded_qml = None
        if form.client_qml_file.data:
            # save uploaded client QML and symbols
            self.save_qgs_style(ows_layer_data, form, False)
        elif form.remove_client_qml.data:
            # remove existing symbols
            self.cleanup_qgs_style_symbols(ows_layer_data.client_qgs_style)
            ows_layer_data.client_qgs_style = None
            # remove uploaded client QML
            self.cleanup_uploaded_qml(ows_layer_data, False)
            ows_layer_data.uploaded_client_qml = None

        # update WMS/WFS
        self.OWSHelper.update_ows(
            ows_layer_data, 'WMS', form.in_wms.data, session
        )
        if is_vector_data_set:
            self.OWSHelper.update_ows(
                ows_layer_data, 'WFS', form.in_wfs.data, session
            )

        # update resource contacts
        self.update_resource_contacts(
            data_set_view, ows_layer_data, form, session
        )

        # update permissions
        self.update_permissions(data_set_view, ows_layer_data, form, session)

    def update_permissions(self, data_set_view, ows_layer_data, form, session):
        """Add or remove permissions for related resources of DataSet.

        :param object data_set_view: data_set_view object
        :param object ows_layer_data: ows_layer_data object
        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        for permission in form.permissions:
            role_id = permission.data['role_id']
            read = permission.data['read']
            write = permission.data['write']

            # get Role from DB
            query = session.query(self.Role).filter_by(id=role_id)
            role = query.first()
            if role is not None:
                # resources for DataSet
                resources = [
                    data_set_view.data_set,
                    data_set_view,
                    ows_layer_data
                ] + data_set_view.attributes

                # update permissions for GDI resources
                for resource in resources:
                    self.PermissionsHelper.update_resource_permission(
                        resource.gdi_oid, role.id, read, False, session
                    )

                edit_config = self.get_edit_config(data_set_view)
                if edit_config is not None:
                    self.PermissionsHelper.update_resource_permission(
                        edit_config.gdi_oid, role.id, read, write, session
                    )

    def update_resource_contacts(self, data_set_view, ows_layer_data, form,
                                 session):
        """Update resource contacts for related resources of DataSet.

        :param object data_set_view: data_set_view object
        :param object ows_layer_data: ows_layer_data object
        :param FlaskForm form: Form for DataSet
        :param Session session: DB session
        """
        # resources for DataSet
        resources = [
            data_set_view.data_set,
            data_set_view,
            ows_layer_data
        ]

        edit_config = self.get_edit_config(data_set_view)
        if edit_config is not None:
            resources.append(edit_config)

        # update resource contacts for GDI resources
        for resource in resources:
            self.ContactsHelper.update_resource_contact(
                resource.gdi_oid, self.ContactsHelper.ROLE_DATA_OWNER,
                form.data_owner.data, session
            )

    def destroy_resource(self, resource, session):
        """Delete existing DataSet records in DB.

        :param object resource: data_set_view object
        :param Session session: DB session
        """
        # resources for DataSet
        data_set_view = resource
        resources = [data_set_view.data_set, data_set_view]
        resources += data_set_view.attributes

        edit_config = self.get_edit_config(data_set_view)
        if edit_config is not None:
            resources.append(edit_config)

        # get associated ows_layer_data
        ows_layers = resource.ows_layers
        if ows_layers:
            ows_layer_data = ows_layers[0]
            resources.append(ows_layer_data)

            # remove OWS layer from WMS/WFS
            self.OWSHelper.update_ows(ows_layer_data, 'WMS', False, session)
            self.OWSHelper.update_ows(ows_layer_data, 'WFS', False, session)

            # Cleanup qml symbols
            self.cleanup_qgs_style_symbols(ows_layer_data.qgs_style)

            # remove uploaded QML
            self.cleanup_uploaded_qml(ows_layer_data)

            # Cleanup client qml symbols
            self.cleanup_qgs_style_symbols(ows_layer_data.client_qgs_style)

            # remove uploaded client QML
            self.cleanup_uploaded_qml(ows_layer_data, False)

        # remove resource contacts
        for resource in resources:
            self.ContactsHelper.remove_resource_contacts(
                resource.gdi_oid, session)

        # remove resource permissions
        for resource in resources:
            self.PermissionsHelper.remove_resource_permissions(
                resource.gdi_oid, session
            )

        # remove data_set_view and associated resources
        session.delete(data_set_view.data_set)
        session.delete(data_set_view)

    def metadata(self):
        """Return table metadata for a data_set as JSON.

        URL params:
            data_source_id: data_source ID
            table_name: Table name as "<schema>.<table>"
        """
        data_source_id = request.args.get('data_source_id')
        table_name = request.args.get('table_name')
        metadata = self.dataset_info(data_source_id, table_name)
        if 'error' not in metadata:
            return jsonify({
                'attributes': metadata.get('attributes'),
                'primary_key': metadata.get('primary_key'),
                'geometry_columns': metadata.get('geometry_columns')
            })
        else:
            # data_set not found or db error
            return jsonify({
                'error': metadata.get('error')
            }), 404

    def dataset_info(self, data_source_id, table_name):
        """Return table metadata for a data_set.

        :param int data_source_id: data_source ID
        :param str table_name: Table name as "<schema>.<table>"
        """
        # NOTE: form field returns 'None' as string if not set
        if not table_name or table_name == 'None':
            # empty table name
            return None

        # parse schema and table name
        parts = table_name.split('.')
        if len(parts) > 1:
            schema = parts[0]
            table_name = parts[1]
        else:
            schema = 'public'

        return self.postgis_metadata(data_source_id, schema, table_name)

    def data_source_tables(self):
        """Return tables for a vector data_source as JSON.

        URL params:
            data_source_id: data_source ID
        """
        data_source_id = request.args.get('data_source_id')
        postgis_tables = self.postgis_tables(data_source_id)
        if 'error' not in postgis_tables:
            return jsonify({
                'tables': postgis_tables.get('tables', [])
            })
        else:
            # data_source not found or db error
            return jsonify({
                'error': postgis_tables.get('error')
            }), 404

    def engine_for_data_source(self, data_source_id):
        """Return SQLAlchemy engine for a data_source.

        :param int data_source_id: data_source ID
        """
        engine = None

        # find data_source
        session = self.session()
        query = session.query(self.DataSource) \
            .filter_by(gdi_oid=data_source_id)
        data_source = query.first()
        session.close()

        if data_source is not None:
            engine = self.db_engine.db_engine(data_source.connection)

        return engine

    def postgis_data_source_choices(self, data_sources):
        """Return select field choices for PostGIS data_sources.

        Filter by PostgreSQL provider and PostGIS extension.

        param list[DataSource]: List of DB DataSources
        """
        postgis_data_sources = []
        for data_source in data_sources:
            try:
                # check DB provider
                if not data_source.connection.startswith('postgresql:'):
                    # not a PostgreSQL provider
                    continue

                # connect to data_source
                engine = self.db_engine.db_engine(data_source.connection)
                conn = engine.connect()

                # check for PostGIS extension

                # build query SQL
                sql = sql_text("""
                    SELECT extname FROM pg_extension
                    WHERE extname = 'postgis' LIMIT 1;
                """)

                # execute query
                result = conn.execute(sql)
                postgis_present = result.first() is not None

                if not postgis_present:
                    # fallback for PostGIS 1.x
                    # check for geometry_columns

                    # build query SQL
                    sql = sql_text("""
                        SELECT table_name FROM information_schema.columns
                        WHERE table_name = 'geometry_columns' LIMIT 1;
                    """)

                    # execute query
                    result = conn.execute(sql)
                    postgis_present = result.first() is not None

                if postgis_present:
                    # add choice if PostGIS present
                    postgis_data_sources.append(
                        (data_source.gdi_oid, data_source.name)
                    )

                # close database connection
                conn.close()
            except OperationalError as e:
                self.logger.warning(
                    "PostGIS Check für %s fehlgeschlagen:\n%s" %
                    (data_source.connection, e.orig)
                )
                # add choice marked with unicode "WARNING SIGN" prefix
                postgis_data_sources.append(
                    (data_source.gdi_oid, u"\u26A0 %s" % data_source.name)
                )

        return postgis_data_sources

    def postgis_tables(self, data_source_id):
        """Return table names for all PostGIS tables of a data_source.

        :param int data_source_id: data_source ID
        """
        tables = []

        try:
            engine = self.engine_for_data_source(data_source_id)
            if engine is None:
                return {
                    'error': "FEHLER: DataSource nicht gefunden"
                }

            # connect to data_source
            conn = engine.connect()

            # get all tables with geometry columns from PostGIS DB

            # build query SQL
            sql = sql_text("""
                SELECT DISTINCT ON (f_table_schema, f_table_name)
                    f_table_schema, f_table_name
                FROM geometry_columns;
            """)

            # execute query
            primary_key = None
            result = conn.execute(sql)
            for row in result:
                tables.append(
                    "%s.%s" % (row['f_table_schema'], row['f_table_name'])
                )

            # close database connection
            conn.close()
        except OperationalError as e:
            self.logger.error(e.orig)
            return {
                'error': "OperationalError: %s" % e.orig
            }
        except ProgrammingError as e:
            self.logger.error(e.orig)
            return {
                'error': "ProgrammingError: %s" % e.orig
            }

        return {
            'tables': tables
        }

    def postgis_metadata(self, data_source_id, schema, table_name):
        """Return attributes, primary key, geometry columns, types and srids
        from a PostGIS table.

        :param int data_source_id: data_source ID
        :param str schema: DB schema name
        :param str table_name: DB table name
        """
        metadata = {}

        try:
            engine = self.engine_for_data_source(data_source_id)
            if engine is None:
                return {
                    'error': "FEHLER: DataSource nicht gefunden"
                }

            # connect to data_source
            conn = engine.connect()

            # get primary key

            # build query SQL
            sql = sql_text("""
                SELECT a.attname
                FROM pg_index i
                    JOIN pg_attribute a ON a.attrelid = i.indrelid
                        AND a.attnum = ANY(i.indkey)
                WHERE i.indrelid = '{schema}.{table}'::regclass
                    AND i.indisprimary;
            """.format(schema=schema, table=table_name))

            # execute query
            primary_key = None
            result = conn.execute(sql)
            for row in result:
                primary_key = row['attname']

            # get geometry column and srid

            # build query SQL
            sql = sql_text("""
                SELECT f_geometry_column, srid, type
                FROM geometry_columns
                WHERE f_table_schema = '{schema}' AND f_table_name = '{table}';
            """.format(schema=schema, table=table_name))

            # execute query
            geometry_columns = []
            result = conn.execute(sql)
            for row in result:
                geometry_columns.append({
                    'geometry_column': row['f_geometry_column'],
                    'geometry_type': row['type'],
                    'srid': row['srid']
                })

            # get other table attributes

            # collect attributes to skip (geometry columns)
            skip_attrs = [
                c['geometry_column'] for c in geometry_columns
            ]

            # build query SQL
            sql = sql_text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = '{schema}' AND table_name = '{table}'
                ORDER BY ordinal_position;
            """.format(schema=schema, table=table_name))

            # execute query
            attributes = []
            result = conn.execute(sql)
            for row in result:
                if row['column_name'] not in skip_attrs:
                    attributes.append(row['column_name'])

            # close database connection
            conn.close()

            metadata = {
                'schema': schema,
                'table': table_name,
                'primary_key': primary_key,
                'attributes': attributes,
                'geometry_columns': geometry_columns
            }
        except OperationalError as e:
            self.logger.error(e.orig)
            return {
                'error': "OperationalError: %s" % e.orig
            }
        except ProgrammingError as e:
            self.logger.error(e.orig)
            return {
                'error': "ProgrammingError: %s" % e.orig
            }

        return metadata

    def data_source_rasters(self):
        """Return raster files for a raster data_source as JSON.

        URL params:
            data_source_id: data_source ID
        """
        data_source_id = request.args.get('data_source_id')
        return jsonify({
            'rasters': self.raster_files(data_source_id)
        })

    def raster_files(self, data_source_id):
        """Return raster filenames for a data_source directory

        :param int data_source_id: data_source ID
        """
        rasters = []

        session = self.session()
        query = session.query(self.DataSource).filter_by(gdi_oid=data_source_id)
        data_source = query.first()
        session.close()

        if data_source is not None:
            raster_dir = data_source.connection
            if os.path.exists(raster_dir):
                # get filenames in data_source dir
                for entry in os.scandir(raster_dir):
                    if not entry.name.startswith('.') and entry.is_file():
                        rasters.append(entry.name)

                rasters.sort()
            else:
                # invalid directory
                msg = "Verzeichnis %s konnte nicht geöffnet werden" % raster_dir
                self.logger.error(msg)
                rasters.append("FEHLER: %s" % msg)

        return rasters

    def json_attributes(self):
        """Try to read attribute data as JSON and return any keys found.

        Expected JSON structure:
            [
                {
                    "<key>": "<value>",
                    "<key2>": "<value2>"
                }
            ]
        """
        json_attrs = []

        data_source_id = request.args.get('data_source_id')
        table_name = request.args.get('table_name')
        attr_name = request.args.get('attr_name')

        try:
            engine = self.engine_for_data_source(data_source_id)
            if engine is None:
                self.logger.error("DataSource nicht gefunden")
                return jsonify({
                    'error': "FEHLER: DataSource nicht gefunden"
                }), 404

            # find potential JSON value

            # connect to data_source
            conn = engine.connect()

            # build query SQL
            # NOTE: also convert native PG json to text
            #       to preserve original order of keys
            sql = sql_text("""
                SELECT {attr}::text AS value
                FROM {table_name}
                WHERE {attr}::text LIKE '[%]'
                LIMIT 1;
            """.format(attr=attr_name, table_name=table_name))

            # execute query
            result = conn.execute(sql)
            for row in result:
                value = row['value']
                try:
                    # parse JSON with original order of keys
                    json_value = json.loads(
                        value, object_pairs_hook=OrderedDict
                    )
                    if type(json_value) is list and len(json_value) > 0:
                        if isinstance(json_value[0], dict):
                            # collect JSON keys from first list entry
                            json_attrs = list(json_value[0].keys())
                except Exception as e:
                    self.logger.warning(
                        "Could not parse value as JSON: '%s'\n%s" % (value, e)
                    )

            # close database connection
            conn.close()
        except Exception as e:
            self.logger.error(
                "JSON Attribute konnten nicht geladen werden: %s" % e
            )
            return jsonify({
                'error': str(e)
            }), 404

        return jsonify({
            'json_attrs': json_attrs
        })

    def download_legend(self, id, filename):
        """Download uploaded legend image.

        :param int id: data_set_view ID
        :param string filename: File name of uploaded legend
                                (only for route, ignored otherwise)
        """
        # find data_set_view
        session = self.session()
        query = session.query(self.DataSetView).filter_by(gdi_oid=id)
        # eager load relations
        query = query.options(joinedload(self.DataSetView.ows_layers))
        data_set_view = query.first()
        session.close()

        if data_set_view is not None:
            # get associated ows_layer_data
            ows_layers = data_set_view.ows_layers
            if ows_layers:
                ows_layer = ows_layers[0]
                if ows_layer.legend_filename:
                    # guess content type from filename
                    filename = ows_layer.legend_filename
                    content_type = mimetypes.guess_type(filename)[0] \
                        or 'application/octet-stream'
                    # return uploaded legend image with original filename
                    return Response(
                        ows_layer.legend_image,
                        content_type=content_type,
                        headers={
                            'content-disposition': 'attachment; filename=%s' %
                            filename
                        },
                        status=200
                    )

        # data_set_view not found or no legend present
        abort(404)

    def download_qml(self, id, filename, for_server=True):
        """Download uploaded QML file.

        :param int id: data_set_view ID
        :param string filename: File name of uploaded QML
                                (only for route, ignored otherwise)
        :param bool for_server: Set if server QML (default: True)
        """
        # find data_set_view
        session = self.session()
        query = session.query(self.DataSetView).filter_by(gdi_oid=id)
        # eager load relations
        query = query.options(joinedload(self.DataSetView.ows_layers))
        data_set_view = query.first()
        session.close()

        if data_set_view is not None:
            # get associated ows_layer_data
            ows_layers = data_set_view.ows_layers
            if ows_layers:
                ows_layer = ows_layers[0]
                if for_server:
                    uploaded_qml = ows_layer.uploaded_qml
                else:
                    uploaded_qml = ows_layer.uploaded_client_qml
                if uploaded_qml:
                    sub_dir = os.path.dirname(uploaded_qml)
                    filename = os.path.basename(uploaded_qml)
                    path = os.path.join(self.uploads_dir(), sub_dir)
                    abspath = os.path.abspath(path)
                    if os.path.exists(os.path.join(abspath, filename)):
                        # return uploaded QML file
                        if filename.endswith('.qml'):
                            mimetype = 'text/xml'
                        else:
                            mimetype = None
                        return send_from_directory(
                            abspath, filename,
                            as_attachment=True, attachment_filename=filename,
                            mimetype=mimetype
                        )
                    else:
                        self.logger.warning(
                            "Could not find uploaded QML file at %s" %
                            os.path.join(abspath, filename)
                        )

        # data_set_view not found or no uploaded QML present
        abort(404)

    def download_client_qml(self, id, filename):
        """Download uploaded client QML file.

        :param int id: data_set_view ID
        :param string filename: File name of uploaded QML
                                (only for route, ignored otherwise)
        """
        return self.download_qml(id, filename, False)

    def save_qgs_style(self, ows_layer_data, form, for_server=True):
        """Extract files from uploaded ZIP file and save symbols and QML
        with adjusted symbol paths.

        :param object ows_layer_data: ows_layer_data object
        :param FlaskForm form: Form for DataSet
        :param bool for_server: Set if server QML (default: True)
        """
        if for_server:
            qgs_style = ows_layer_data.qgs_style
            qml_file_field = form.qml_file
        else:
            qgs_style = ows_layer_data.client_qgs_style
            qml_file_field = form.client_qml_file

        self.cleanup_qgs_style_symbols(qgs_style)
        try:
            if qml_file_field.data.filename.endswith('.qml'):
                # save uploaded QML
                qml_data = request.files[qml_file_field.name].read()
                if for_server:
                    ows_layer_data.qgs_style = qml_data.decode()
                else:
                    ows_layer_data.client_qgs_style = qml_data.decode()
            else:
                # open uploaded ZIP data
                zip_file = zipfile.ZipFile(request.files[qml_file_field.name])

                # read first top-level QML
                qml_pattern = re.compile("^[^\/\\\\]+\.qml$")
                qml_data = None
                for filename in zip_file.namelist():
                    if qml_pattern.match(filename):
                        self.logger.info("Using QML: %s" % filename)
                        qml_data = zip_file.open(filename).read().decode()
                        break
                if qml_data is not None:
                    # parse XML
                    root = ElementTree.fromstring(qml_data)

                    # save and update symbols
                    self.update_qml_symbols(root, 'SvgMarker', 'name', zip_file)
                    self.update_qml_symbols(root, 'SVGFill', 'svgFile',
                                            zip_file)
                    self.update_qml_symbols(root, 'RasterFill', 'imageFile',
                                            zip_file)

                    # save QML
                    qml_data = ElementTree.tostring(
                        root, encoding='utf-8', method='xml'
                    )
                    if for_server:
                        ows_layer_data.qgs_style = qml_data.decode()
                    else:
                        ows_layer_data.client_qgs_style = qml_data.decode()
                else:
                    self.raise_validation_error(
                        qml_file_field, "ZIP enthält kein QML"
                    )

            # cleanup any previous upload
            self.cleanup_uploaded_qml(ows_layer_data, for_server)

            # create target dir
            sub_dir = str(uuid.uuid4())
            target_dir = os.path.join(self.uploads_dir(), sub_dir)
            os.makedirs(target_dir, 0o755, True)

            # save uploaded original file
            filename = qml_file_field.data.filename
            with open(os.path.join(target_dir, filename), 'wb') as f:
                # reset file stream
                request.files[qml_file_field.name].seek(0)

                f.write(request.files[qml_file_field.name].read())

            # save path to uploaded file
            if for_server:
                ows_layer_data.uploaded_qml = os.path.join(sub_dir, filename)
            else:
                ows_layer_data.uploaded_client_qml = os.path.join(sub_dir,
                                                                  filename)
        except zipfile.BadZipFile as e:
            self.raise_validation_error(
                qml_file_field, "Datei ist kein ZIP"
            )
        except UnicodeDecodeError:
            self.raise_validation_error(
                qml_file_field, "QML Encoding ist nicht UTF-8"
            )

    def update_qml_symbols(self, root, layer_class, prop_key, zip_file):
        """Save symbol resources with hashed filename and update symbol paths in QML.

        :param xml.etree.ElementTree.Element root: XML root node
        :param str layer_class: Symbol layer class
        :param str prop_key: Symbol layer prop key for symbol path
        :param zipfile.ZipFile zip_file: ZIP file
        """
        for svgprop in root.findall(".//layer[@class='%s']/prop[@k='%s']" %
                                    (layer_class, prop_key)):
            symbol_path = svgprop.get('v')
            symbol_filename = os.path.basename(symbol_path)

            # NOTE: assume symbols not included in ZIP are default symbols
            if symbol_filename in zip_file.namelist():
                # convert full symbol path to MD5
                m = hashlib.md5()
                md5 = m.update(symbol_path.encode())
                extension = os.path.splitext(symbol_filename)[1]
                new_filename = "%s%s" % (m.hexdigest(), extension)

                # update relative symbol path in QML
                new_path = os.path.join(self.SYMBOLS_SUB_DIR, new_filename)
                svgprop.set('v', new_path)

                self.logger.info("Save and update symbol: %s => %s" %
                                 (symbol_path, new_path))

                # save symbol file with hashed filename
                target_path = os.path.join(self.symbols_dir(), new_filename)
                with open(target_path, 'wb') as f:
                    f.write(zip_file.open(symbol_filename).read())

    def get_edit_config(self, data_set_view):
        """Get any associated data_set_edit for a data_set_view.

        :param object data_set_view: data_set_view object
        """
        edit_config = None

        # get associated data_set_edit
        edit_configs = data_set_view.data_set_edit_collection
        if edit_configs:
            edit_config = edit_configs[0]

        return edit_config

    def cleanup_qgs_style_symbols(self, qml_data):
        """ Cleanup files referenced by QML
        :param string qgs_style: The QML style
        """

        if not qml_data:
            return

        root = ElementTree.fromstring(qml_data)

        for layer_class, prop_key in [('SvgMarker', 'name'), ('SVGFill', 'svgFile'), ('RasterFill', 'imageFile')]:
            for svgprop in root.findall(".//layer[@class='%s']/prop[@k='%s']" %
                                    (layer_class, prop_key)):
                symbol_path = svgprop.get('v')

                try:
                    os.remove(os.path.join(
                        self.symbols_dir(), os.path.basename(symbol_path))
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to remove: %s\n%s" % (symbol_path, e)
                    )

    def cleanup_uploaded_qml(self, ows_layer_data, for_server=True):
        """Cleanup uploaded QML file.

        :param object ows_layer_data: ows_layer_data object
        :param bool for_server: Set if server QML (default: True)
        """
        if for_server:
            uploaded_qml = ows_layer_data.uploaded_qml
        else:
            uploaded_qml = ows_layer_data.uploaded_client_qml

        if uploaded_qml:
            try:
                sub_dir = os.path.dirname(uploaded_qml)
                filename = os.path.basename(uploaded_qml)
                path = os.path.join(self.uploads_dir(), sub_dir)
                os.remove(os.path.join(path, filename))
                os.rmdir(path)
            except Exception as e:
                self.logger.warning(
                    "Failed to remove uploaded QML %s: %s" % (uploaded_qml, e)
                )

    def qgs_dir(self):
        """Return target base dir for QGS files from service config."""
        # get dir from service config
        config = self.service_config()
        return config.get('project_output_dir', '/tmp/')

    def symbols_dir(self):
        """Return target dir for QGS symbols from service config."""
        return os.path.join(self.qgs_dir(), self.SYMBOLS_SUB_DIR)

    def uploads_dir(self):
        """Return target dir for QML uploads from service config."""
        return os.path.join(self.qgs_dir(), self.UPLOADS_SUB_DIR)
