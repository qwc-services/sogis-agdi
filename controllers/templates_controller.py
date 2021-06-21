import hashlib
import os
import re
import requests
import shutil
from urllib.parse import urlencode
import uuid
import zipfile
from xml.etree import ElementTree

from flask import abort, flash, render_template, request, Response, \
    send_from_directory, stream_with_context, url_for

from .contacts_helper import ContactsHelper
from .controller import Controller
from .ows_helper import OWSHelper
from .permissions_helper import PermissionsHelper
from forms import TemplateForm


class TemplatesController(Controller):
    """Controller for Template GUI

    Manage templates and related models from combined GUI.
    """

    # subdir for QPT resources relative to PROJECT_OUTPUT_DIR
    PRINT_RESOURCES_SUB_DIR = 'print'

    # subdir for uploaded files
    # relative to PROJECT_OUTPUT_DIR resp. JASPER_REPORTS_DIR
    UPLOADS_SUB_DIR = 'uploads'

    def __init__(self, app, config_models, service_config):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param func service_config: Helper method for reading service config
        """
        super(TemplatesController, self).__init__(
            "Template", 'templates', 'template', 'templates_gui', app,
            config_models
        )
        self.service_config = service_config
        self.ContactsHelper = ContactsHelper(config_models, app.logger)
        self.OWSHelper = OWSHelper(config_models)
        self.PermissionsHelper = PermissionsHelper(config_models)

        self.Template = self.config_models.model('template')
        self.TemplateJasper = self.config_models.model('template_jasper')
        self.TemplateInfo = self.config_models.model('template_info')
        self.TemplateQGIS = self.config_models.model('template_qgis')
        self.DataSet = self.config_models.model('data_set')
        self.OWSLayer = self.config_models.model('ows_layer')

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # download uploaded Jasper report
        app.add_url_rule(
            '/%s/<int:id>/jasper/<string:filename>' % base_route,
            '%s_jasper' % suffix, self.download_jasper, methods=['GET']
        )
        # download uploaded info template
        app.add_url_rule(
            '/%s/<int:id>/info/<string:filename>' % base_route,
            '%s_info' % suffix, self.download_info, methods=['GET']
        )
        # download uploaded QPT
        app.add_url_rule(
            '/%s/<int:id>/qpt/<string:filename>' % base_route,
            '%s_qpt' % suffix, self.download_qpt, methods=['GET']
        )
        # generate document from uploaded Jasper report
        app.add_url_rule(
            '/%s/<int:id>/report' % base_route,
            'generate_report', self.generate_report, methods=['GET']
        )
        app.add_url_rule(
            '/%s/<int:id>/report/<string:name>' % base_route,
            'render_report', self.render_report, methods=['GET']
        )

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return templates list.

        :param Session session: DB session
        """
        return session.query(self.Template) \
            .order_by(self.Template.type, self.Template.name).all()

    def form_for_new(self):
        """Return form for new template."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Template."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Template records in DB.

        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Template by Template ID.

        :param int id: Template ID
        :param Session session: DB session
        """
        return session.query(self.Template).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Template.

        :param object resource: Template object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Template.

        :param object resource: template object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Template records in DB.

        :param object resource: template object
        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional template object
        :param bool edit_form: Set if edit form
        """
        form = TemplateForm(self.config_models, obj=resource)

        if edit_form:
            # select responsible contact
            form.responsible.data = self.ContactsHelper.resource_contact_id(
                resource.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE
            )

            # show that template file is present
            if resource.type == 'jasper':
                form.jasper_file.description = "JasperReports Report vorhanden"

                if resource.uploaded_report:
                    # add download link for uploaded report
                    filename = os.path.basename(resource.uploaded_report)
                    form.jasper_file.description = (
                        'JasperReports Report vorhanden: '
                        '<a href="jasper/%s" target="_blank">%s</a>' %
                        (filename, filename)
                    )
            elif resource.type == 'info':
                form.info_file.description = "HTML Template vorhanden"

                if resource.template_filename:
                    # add download link for uploaded info template
                    filename = os.path.basename(resource.template_filename)
                    form.info_file.description = (
                        'HTML Template vorhanden: '
                        '<a href="info/%s" target="_blank">%s</a>' %
                        (filename, filename)
                    )
            elif resource.type == 'qgis':
                form.qgis_file.description = "QGIS Drucklayout vorhanden"

                if resource.uploaded_qpt:
                    # add download link for uploaded QPT
                    filename = os.path.basename(resource.uploaded_qpt)
                    form.qgis_file.description = (
                        'QGIS Drucklayout vorhanden: '
                        '<a href="qpt/%s" target="_blank">%s</a>' %
                        (filename, filename)
                    )

            if resource.type == 'jasper':
                # add data products for resource on edit
                for ows_layer in resource.ows_layers:
                    form.data_products.append_entry({
                        'data_product_id': ows_layer.gdi_oid,
                        'data_product_name': ows_layer.name
                    })

                # add data sets for resource on edit
                for data_set in resource.data_sets:
                    form.datasets.append_entry({
                        'data_set_id': data_set.gdi_oid,
                        'data_set_name': data_set.data_set_name
                    })

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

        # get OWS layers
        query = session.query(self.OWSLayer).order_by(self.OWSLayer.name)
        # skip WMS root layers
        root_layers = self.OWSHelper.ows_root_layers(session)
        root_layer_ids = [l.gdi_oid for l in root_layers]
        if root_layer_ids:
            query = query.filter(~self.OWSLayer.gdi_oid.in_(root_layer_ids))

        ows_layers = query.all()

        # get data sets
        query = session.query(self.DataSet) \
            .order_by(self.DataSet.data_set_name) \
            .distinct(
                self.DataSet.gdi_oid_data_source, self.DataSet.data_set_name
            )
        data_sets = query.all()
        session.close()

        # set choices for responsible select field
        form.responsible.choices = [(0, "")] + \
            self.ContactsHelper.person_choices()

        # set choices for data product select field
        form.data_product.choices = [(0, "")] + [
            (d.gdi_oid, d.name) for d in ows_layers
        ]

        # set choices for data set select field
        form.data_set.choices = [(0, "")] + [
            (d.gdi_oid, d.data_set_name) for d in data_sets
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
        """Create or update Template records in DB.

        :param object resource: Optional template object
                                (None for create)
        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        if resource is None:
            # create new template
            if form.type.data == 'jasper':
                template = self.TemplateJasper()
            elif form.type.data == 'info':
                template = self.TemplateInfo()
            elif form.type.data == 'qgis':
                template = self.TemplateQGIS()
            else:
                template = self.Template()
            session.add(template)
        else:
            # update existing template
            template = resource

        # update template
        template.name = form.name.data
        template.description = form.description.data

        # type specific fields
        if form.type.data == 'jasper':
            if form.jasper_file.data:
                # save uploaded JasperReports file
                self.save_jasper_report(template, form)
            elif template.report_filename is None:
                # upload missing for new template
                self.raise_validation_error(
                    form.jasper_file, "Kein JasperReports Report ausgewählt"
                )

            # update default format
            if form.default_format.data:
                template.default_format = form.default_format.data
            else:
                template.default_format = None

            # update data products
            self.update_data_products(template, form, session)

            # update data sets
            self.update_data_sets(template, form, session)

        elif form.type.data == 'info':
            if form.info_file.data:
                # save uploaded info HTML
                self.save_info_html(template, form)
            elif template.info_template is None:
                # upload missing for new template
                self.raise_validation_error(
                    form.info_file, "Kein Info Template ausgewählt"
                )

            # update info type
            template.info_type = form.info_type.data

            # update info fields
            if template.info_type == 'sql':
                if form.info_sql.data:
                    # update info SQL
                    template.info_sql = form.info_sql.data
                else:
                    # empty info SQL
                    self.raise_validation_error(
                        form.info_sql, "SQL Query darf nicht leer sein"
                    )
                template.info_module = None
            elif template.info_type == 'module':
                if form.info_module.data:
                    # update info module
                    template.info_module = form.info_module.data
                else:
                    # empty info module
                    self.raise_validation_error(
                        form.info_module,
                        "Name des Moduls darf nicht leer sein"
                    )
                template.info_sql = None
            else:
                template.info_sql = None
                template.info_module = None

        elif form.type.data == 'qgis':
            if form.qgis_file.data:
                # save uploaded QPT and resources
                self.save_qgs_print_layout(template, form)
            elif template.qgs_print_layout is None:
                # upload missing for new template
                self.raise_validation_error(
                    form.qgis_file, "Kein QGIS Drucklayout ausgewählt"
                )

            # update composer name with template name
            self.update_qpt_name(template, form.name.data)

        # NOTE: flush object changes in session to update gdi_oid of a
        #       new template
        session.flush()

        # update resource contact
        self.ContactsHelper.update_resource_contact(
            template.gdi_oid, self.ContactsHelper.ROLE_RESPONSIBLE,
            form.responsible.data, session
        )

        # update permissions
        self.update_permissions(template, form, session)

    def destroy_resource(self, resource, session):
        """Delete existing Template records in DB.

        :param object resource: template object
        :param Session session: DB session
        """
        # remove template, resource contact and permissions
        template = resource
        self.ContactsHelper.remove_resource_contacts(
            template.gdi_oid, session
        )
        self.PermissionsHelper.remove_resource_permissions(
            template.gdi_oid, session
        )

        if template.type == 'jasper':
            # remove data_sets
            data_sets = [
                data_set for data_set in template.data_sets
            ]
            for data_set in data_sets:
                template.data_set_collection.remove(data_set)
                session.delete(data_set)

        self.cleanup_template_data(template)
        self.cleanup_uploaded_files(template)
        session.delete(template)

    def download_jasper(self, id, filename):
        """Download uploaded JasperReports file.

        :param int id: Template ID
        :param str filename: File name of uploaded report
                             (only for route, ignored otherwise)
        """
        # find template_jasper
        session = self.session()
        query = session.query(self.TemplateJasper).filter_by(gdi_oid=id)
        template_jasper = query.first()
        session.close()

        if template_jasper is not None and template_jasper.uploaded_report:
            # return uploaded JasperReports file
            return self.send_uploaded_file(
                self.jasper_uploads_dir(), template_jasper.uploaded_report,
                "JasperReports report"
            )

        # template_jasper not found or no uploaded report present
        abort(404)

    def download_info(self, id, filename):
        """Download uploaded info template.

        :param int id: Template ID
        :param str filename: File name of uploaded HTML
                             (only for route, ignored otherwise)
        """
        # find template_info
        session = self.session()
        query = session.query(self.TemplateInfo).filter_by(gdi_oid=id)
        template_info = query.first()
        session.close()

        if template_info is not None and template_info.template_filename:
            # return uploaded info template with original filename
            return Response(
                template_info.info_template,
                content_type='text/html',
                headers={
                    'content-disposition': 'attachment; filename=%s' %
                    filename
                },
                status=200
            )

        # template_info not found or no info template present
        abort(404)

    def download_qpt(self, id, filename):
        """Download uploaded QPT file.

        :param int id: Template ID
        :param str filename: File name of uploaded QPT
                             (only for route, ignored otherwise)
        """
        # find template_qgis
        session = self.session()
        query = session.query(self.TemplateQGIS).filter_by(gdi_oid=id)
        template_qgis = query.first()
        session.close()

        if template_qgis is not None and template_qgis.uploaded_qpt:
            # return uploaded QPT file
            return self.send_uploaded_file(
                self.qpt_uploads_dir(), template_qgis.uploaded_qpt, "QPT"
            )

        # template_qgis not found or no uploaded QGS present
        abort(404)

    def send_uploaded_file(self, uploads_dir, upload_path, file_type):
        """Helper for sending an uploaded template file.

        :param str uploads_dir: Base dir for uploaded files
        :param str upload_path: Path to uploaded file relative to uploads_dir
        :param str file_type: Description of file type for warnings
        """
        sub_dir = os.path.dirname(upload_path)
        filename = os.path.basename(upload_path)
        path = os.path.join(uploads_dir, sub_dir)
        abspath = os.path.abspath(path)
        if os.path.exists(os.path.join(abspath, filename)):
            # return uploaded file
            if filename.endswith('.jrxml') or filename.endswith('.qpt'):
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
                "Could not find uploaded %s file at %s" %
                (file_type, os.path.join(abspath, filename))
            )

        # uploaded file not found
        abort(404)

    def generate_report(self, id):
        """Show form for generating a document from an uploaded JasperReports
        report.

        :param int id: Template ID
        """
        # find template_jasper
        session = self.session()
        query = session.query(self.TemplateJasper).filter_by(gdi_oid=id)
        template_jasper = query.first()
        session.close()

        if template_jasper is None:
            # template_jasper not found
            abort(404)
            return

        fields = []
        try:
            # parse XML
            filepath = os.path.join(
                self.jasper_reports_dir(), template_jasper.report_filename
            )
            root = ElementTree.parse(filepath).getroot()
            ns = {'ns': 'http://jasperreports.sourceforge.net/jasperreports'}

            # collect report parameters
            for parameter in root.findall("ns:parameter", ns):
                # get any description
                description = None
                desc = parameter.find("ns:parameterDescription", ns)
                if desc is not None and desc.text:
                    description = desc.text
                    if (description.startswith('"') and
                            description.endswith('"')):
                        # remove enclosing quotes
                        description = description[1:-1]

                # get any default value
                default_value = None
                default = parameter.find("ns:defaultValueExpression", ns)
                if default is not None and default.text:
                    default_value = default.text
                    if (default_value.startswith('"') and
                            default_value.endswith('"')):
                        # remove enclosing quotes
                        default_value = default_value[1:-1]

                # get field type
                field_type = 'text'
                param_class = parameter.get('class')
                if param_class == 'java.lang.Integer':
                    field_type = 'number'

                fields.append({
                    'name': parameter.get('name'),
                    'description': description,
                    'type': field_type,
                    'default_value': default_value
                })
        except Exception as e:
            self.logger.error(e)
            flash('Exception: %s' % e, 'error')

        # show report form
        template = '%s/report.html' % self.templates_dir
        title = "Report"
        action = url_for('render_report', id=id, name=template_jasper.name)

        return render_template(
            template, title=title, template_name=template_jasper.name,
            action=action, fields=fields
        )

    def render_report(self, id, name):
        """Forward params to JasperReports service and return response.

        :param int id: Template ID
        :param str name: Template name (only for route, ignored otherwise)
        """
        # find template_jasper
        session = self.session()
        query = session.query(self.TemplateJasper).filter_by(gdi_oid=id)
        template_jasper = query.first()
        session.close()

        if template_jasper is None:
            # template_jasper not found
            abort(404)
            return

        # forward to JasperReports service
        # cf. ../../rest_services/document_service/server.py get_document()
        jasper_template = os.path.splitext(template_jasper.report_filename)[0]
        url = "%s/%s/" % (self.jasper_service_url(), jasper_template)
        params = request.args.copy()
        if not params.get('format'):
            # default to PDF
            params['format'] = 'pdf'

        self.logger.info("Forward request to %s?%s" % (url, urlencode(params)))

        response = requests.get(
            url, params=params, stream=True, timeout=self.jasper_timeout()
        )
        res = Response(
            stream_with_context(response.iter_content(chunk_size=16*1024)),
            content_type=response.headers['content-type'],
            status=response.status_code
        )
        if response.status_code == requests.codes.ok:
            filename = "%s.%s" % (
                template_jasper.name, params.get('format', 'pdf')
            )
            res.headers['content-disposition'] = "filename=%s" % filename
        return res

    def save_jasper_report(self, template, form):
        """Save uploaded JasperReports report.

        :param object template: template object
        :param FlaskForm form: Form for Template
        """

        # Cleanup previous report
        self.cleanup_template_data(template)

        try:

            is_zip = not form.jasper_file.data.filename.endswith('.jrxml')
            if is_zip:
                # open uploaded ZIP data
                zip_file = zipfile.ZipFile(request.files[form.jasper_file.name])

                for filename in zip_file.namelist():
                    if filename == "master.jrxml":
                        break
                else:
                    self.raise_validation_error(
                        form.jasper_file, "ZIP enthält kein master.jrxml"
                    )

                # create uuid directory
                extractdir = str(uuid.uuid4())
                extractpath = os.path.join(self.jasper_reports_dir(), extractdir)
                os.mkdir(extractpath, 0o755)

                zip_file.extractall(extractpath)

                # save report filename
                template.report_filename = extractdir + "/master.jrxml"

            else:
                # create uuid directory
                subdir = str(uuid.uuid4())
                target_dir = os.path.join(self.jasper_reports_dir(), subdir)
                os.mkdir(target_dir, 0o755)

                # save uploaded JRXML file
                target_path = os.path.join(
                    target_dir, form.jasper_file.data.filename
                )

                with open(target_path, 'wb') as f:
                    f.write(request.files[form.jasper_file.name].read())

                # save report filename
                template.report_filename = os.path.join(
                    subdir, form.jasper_file.data.filename
                )

            # cleanup any previous upload
            self.cleanup_uploaded_files(template)

            # create target dir
            sub_dir = str(uuid.uuid4())
            target_dir = os.path.join(self.jasper_uploads_dir(), sub_dir)
            os.makedirs(target_dir, 0o755, True)

            # save uploaded original file
            filename = form.jasper_file.data.filename
            with open(os.path.join(target_dir, filename), 'wb') as f:
                # reset file stream
                request.files[form.jasper_file.name].seek(0)

                f.write(request.files[form.jasper_file.name].read())

            # save path to uploaded file
            template.uploaded_report = os.path.join(sub_dir, filename)
        except zipfile.BadZipFile as e:
            self.raise_validation_error(
                form.qgis_file, "Datei ist kein ZIP"
            )
        except FileNotFoundError as e:
            self.logger.error(e)
            self.raise_validation_error(
                form.jasper_file,
                "Datei oder Verzeichnis nicht gefunden: '%s'" % target_path
            )
        except PermissionError as e:
            self.logger.error(e)
            self.raise_validation_error(
                form.jasper_file,
                "Keine Zugriffsberechtigung für '%s'" % target_path
            )

    def save_info_html(self, template, form):
        """Save uploaded info HTML.

        :param object template: template object
        :param FlaskForm form: Form for Template
        """
        try:
            # save info HTML
            info_file = request.files[form.info_file.name]
            template.info_template = info_file.read().decode()
            template.template_filename = form.info_file.data.filename
        except UnicodeDecodeError:
            self.raise_validation_error(
                form.info_file, "HTML Encoding ist nicht UTF-8"
            )

    def save_qgs_print_layout(self, template, form):
        """Extract files from uploaded ZIP file and save resources and QPT
        with adjusted resource paths.

        :param object template: template object
        :param FlaskForm form: Form for Template
        """
        try:
            is_zip = not form.qgis_file.data.filename.endswith('.qpt')
            if is_zip:
                # open uploaded ZIP data
                zip_file = zipfile.ZipFile(request.files[form.qgis_file.name])

                # read first top-level QPT
                qpt_pattern = re.compile("^[^\/\\\\]+\.qpt$")
                qpt_data = None
                for filename in zip_file.namelist():
                    if qpt_pattern.match(filename):
                        self.logger.info("Using QPT: %s" % filename)
                        qpt_data = zip_file.open(filename).read().decode()
                        break

                if qpt_data is None:
                    self.raise_validation_error(
                        form.qgis_file, "ZIP enthält kein QPT"
                    )
            else:
                # read uploaded QPT
                qpt_data = request.files[form.qgis_file.name].read()

            # Cleanup previous QPT auxiliary files
            self.cleanup_template_data(template)

            if qpt_data is not None:
                # parse XML
                root = ElementTree.fromstring(qpt_data)

                if is_zip:
                    # save and update resources from ZIP
                    self.update_qpt_resources(root, zip_file)

                # extract size of first map item
                template.map_width = 0
                template.map_height = 0
                for item in root.findall(".//ComposerMap/ComposerItem"):
                    template.map_width = item.get('width')
                    template.map_height = item.get('height')
                    break

                # extract label ids
                labels = []
                for item in root.findall(".//ComposerLabel/ComposerItem"):
                    labelId = item.get("id")
                    if labelId:
                        labels.append(labelId.replace(",", r"\,"))
                template.print_labels = ",".join(labels)

                # save QPT
                qpt_data = ElementTree.tostring(
                    root, encoding='utf-8', method='xml'
                )
                template.qgs_print_layout = qpt_data.decode()

            # cleanup any previous upload
            self.cleanup_uploaded_files(template)

            # create target dir
            sub_dir = str(uuid.uuid4())
            target_dir = os.path.join(self.qpt_uploads_dir(), sub_dir)
            os.makedirs(target_dir, 0o755, True)

            # save uploaded original file
            filename = form.qgis_file.data.filename
            with open(os.path.join(target_dir, filename), 'wb') as f:
                # reset file stream
                request.files[form.qgis_file.name].seek(0)

                f.write(request.files[form.qgis_file.name].read())

            # save path to uploaded file
            template.uploaded_qpt = os.path.join(sub_dir, filename)
        except zipfile.BadZipFile as e:
            self.raise_validation_error(
                form.qgis_file, "Datei ist kein ZIP"
            )
        except UnicodeDecodeError:
            self.raise_validation_error(
                form.qgis_file, "QPT Encoding ist nicht UTF-8"
            )

    def update_qpt_resources(self, root, zip_file):
        """Save resources with hashed filename and update resource paths in QPT.

        :param xml.etree.ElementTree.Element root: XML root node
        :param zipfile.ZipFile zip_file: ZIP file
        """
        for picture in root.findall(".//ComposerPicture"):
            resource_path = picture.get('file')
            resource_filename = os.path.basename(resource_path)

            if resource_filename in zip_file.namelist():
                # convert full resource path to MD5
                m = hashlib.md5()
                md5 = m.update(resource_filename.encode())
                extension = os.path.splitext(resource_filename)[1]
                new_filename = "%s%s" % (m.hexdigest(), extension)

                # update relative resource path in QPT
                new_path = os.path.join(
                    self.PRINT_RESOURCES_SUB_DIR, new_filename
                )
                picture.set('file', new_path)

                self.logger.info("Save and update print resource: %s => %s" %
                                 (resource_path, new_path))

                # save resource file with hashed filename
                target_path = os.path.join(
                    self.print_resources_dir(), new_filename
                )
                with open(target_path, 'wb') as f:
                    f.write(zip_file.open(resource_filename).read())
            else:
                self.logger.warning("Missing QPT resource: %s" % resource_path)

    def update_qpt_name(self, template, name):
        """Update composer name in QPT.

        :param object template: template object
        :param str name: New composer name
        """
        # parse XML
        root = ElementTree.fromstring(template.qgs_print_layout)

        # root is <Composer>
        if root.get('title') != name:
            # update composer name
            root.set('title', name)

            # update QPT
            qpt_data = ElementTree.tostring(
                root, encoding='utf-8', method='xml'
            )
            template.qgs_print_layout = qpt_data.decode()

    def update_data_products(self, template, form, session):
        """Add or remove data products for template.

        :param object template: template object
        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        # lookup for ows_layer of template
        template_data_products = {}
        for ows_layer in template.ows_layers:
            template_data_products[ows_layer.gdi_oid] = ows_layer

        # update data products
        data_product_ids = []
        for data_product in form.data_products:
            # get ows_layer from ConfigDB
            data_product_id = int(data_product.data['data_product_id'])
            query = session.query(self.OWSLayer) \
                .filter_by(gdi_oid=data_product_id)
            ows_layer = query.first()

            if ows_layer is not None:
                data_product_ids.append(data_product_id)
                if data_product_id not in template_data_products:
                    # add ows_layer to template
                    template.ows_layers.append(ows_layer)

        # remove removed data products
        for ows_layer in template_data_products.values():
            if ows_layer.gdi_oid not in data_product_ids:
                # remove ows_layer from template
                template.ows_layers.remove(ows_layer)

    def update_data_sets(self, template, form, session):
        """Add or remove source data sets for template.

        NOTE: create separate data_sets for each template.

        :param object template: template object
        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        # lookup for data_set of template
        template_data_sets = {}
        for data_set in template.data_sets:
            template_data_sets[data_set.gdi_oid] = data_set

        # update data sets
        data_set_ids = []
        for data_set in form.datasets:
            # get data_set from ConfigDB
            data_set_id = int(data_set.data['data_set_id'])
            query = session.query(self.DataSet) \
                .filter_by(gdi_oid=data_set_id)
            data_set = query.first()

            if data_set is not None:
                if data_set_id in data_set_ids:
                    # skip duplicates
                    continue

                if data_set_id not in template_data_sets:
                    # copy data_set
                    new_data_set = self.DataSet()
                    new_data_set.data_set_name = data_set.data_set_name
                    new_data_set.gdi_oid_data_source = \
                        data_set.gdi_oid_data_source

                    # add data_set to template
                    template.data_set_collection.append(new_data_set)
                    session.add(new_data_set)

                    # mark original id from form
                    data_set_ids.append(data_set.gdi_oid)

                    data_set = new_data_set
                # else update existing data_set

                # update data_set
                data_set.name = form.name.data
                data_set.description = form.description.data

                data_set_ids.append(data_set.gdi_oid)

        # remove removed data sets
        for data_set in template_data_sets.values():
            if data_set.gdi_oid not in data_set_ids:
                # remove data_set from template
                template.data_set_collection.remove(data_set)
                # remove data_set
                session.delete(data_set)

    def update_permissions(self, template, form, session):
        """Add or remove permissions for template.

        :param object template: template object
        :param FlaskForm form: Form for Template
        :param Session session: DB session
        """
        for permission in form.permissions:
            role_id = permission.data['role_id']
            read = permission.data['read']

            role = self.PermissionsHelper.role(role_id)
            if role is not None:
                # update permissions for template
                self.PermissionsHelper.update_resource_permission(
                    template.gdi_oid, role.id, read, False, session
                )

    def cleanup_template_data(self, template):
        """ Cleanup files belonging to template.

        :param object template: template object
        """
        # Cleanup jasper reports
        if isinstance(template, self.TemplateJasper) and template.report_filename:
            subdir = os.path.dirname(template.report_filename)
            if subdir and os.path.isdir(os.path.join(
                self.jasper_reports_dir(), subdir)
            ):
                try:
                    shutil.rmtree(os.path.join(
                        self.jasper_reports_dir(), subdir)
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to cleanup jasper report: %s" %
                        template.report_filename
                    )
            elif os.path.isfile(os.path.join(
                self.jasper_reports_dir(), template.report_filename)
            ):
                try:
                    os.remove(os.path.join(
                        self.jasper_reports_dir(), template.report_filename)
                    )
                except Exception as e:
                    self.logger.warning(
                        "Failed to cleanup jasper report: %s" %
                        template.report_filename
                    )

        # Cleanup auxiliary QPT files
        if isinstance(template, self.TemplateQGIS) and template.qgs_print_layout:
            root = ElementTree.fromstring(template.qgs_print_layout)
            for picture in root.findall(".//ComposerPicture"):
                filename = picture.get('file')
                try:
                    os.remove(os.path.join(
                        self.print_resources_dir(), os.path.basename(filename))
                    )
                except Exception as e:
                    self.logger.warning("Failed to remove: %s" % filename)

    def cleanup_uploaded_files(self, template):
        """ Cleanup uploaded template files.

        :param object template: template object
        """
        upload_path = None
        if template.type == 'jasper':
            uploads_dir = self.jasper_uploads_dir()
            upload_path = template.uploaded_report
            file_type = "JasperReports report"
        elif template.type == 'qgis':
            uploads_dir = self.qpt_uploads_dir()
            upload_path = template.uploaded_qpt
            file_type = "QPT"

        if upload_path:
            try:
                sub_dir = os.path.dirname(upload_path)
                filename = os.path.basename(upload_path)
                path = os.path.join(uploads_dir, sub_dir)
                os.remove(os.path.join(path, filename))
                os.rmdir(path)
            except Exception as e:
                self.logger.warning(
                    "Failed to remove uploaded %s %s: %s" %
                    (file_type, upload_path, e)
                )

    def qgs_dir(self):
        """Return target base dir for QGS files from service config."""
        # get dir from service config
        config = self.service_config()
        return config.get('project_output_dir', '/tmp/')

    def print_resources_dir(self):
        """Return target dir for QPT resources."""
        return os.path.join(self.qgs_dir(), self.PRINT_RESOURCES_SUB_DIR)

    def qpt_uploads_dir(self):
        """Return target dir for QPT uploads."""
        return os.path.join(self.qgs_dir(), self.UPLOADS_SUB_DIR)

    def jasper_reports_dir(self):
        """Return target dir for JasperReports reports."""
        # get dir from service config
        config = self.service_config()
        return config.get('jasper_reports_dir', '/tmp/')

    def jasper_uploads_dir(self):
        """Return target dir for JasperReports uploads."""
        return os.path.join(self.jasper_reports_dir(), self.UPLOADS_SUB_DIR)

    def jasper_service_url(self):
        """Return JasperReports service URL."""
        # get URL from service config
        config = self.service_config()
        return config.get('jasper_service_url', 'http://localhost:8002/reports')

    def jasper_timeout(self):
        """Return JasperReports timeout."""
        # get timeout from service config
        config = self.service_config()
        return config.get('jasper_timeout', 60)
