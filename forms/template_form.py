import re

from flask_wtf import FlaskForm
from werkzeug.datastructures import FileStorage
from wtforms import BooleanField, FieldList, FileField, FormField, \
    HiddenField, RadioField, SelectField, StringField, SubmitField, \
    TextAreaField, ValidationError
from wtforms.validators import DataRequired, Optional


class DataProductForm(FlaskForm):
    """Subform for data products"""
    data_product_id = HiddenField('DataProduct-ID', validators=[DataRequired()])
    data_product_name = HiddenField('DataProduct', validators=[Optional()])


class DataSetForm(FlaskForm):
    """Subform for data sets"""
    data_set_id = HiddenField('DataSet-ID', validators=[DataRequired()])
    data_set_name = HiddenField('DataSet', validators=[Optional()])


class PermissionForm(FlaskForm):
    """Subform for permissions"""
    role_id = HiddenField('Rollen-ID', validators=[DataRequired()])
    role_name = HiddenField('Rolle', validators=[Optional()])
    read = BooleanField('Lesen')


class TemplateForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    description = TextAreaField('Beschreibung', validators=[DataRequired()])
    responsible = SelectField(
        'Verantwortlicher', coerce=int,
        validators=[DataRequired(message="Kein Verantwortlicher ausgewählt")]
    )
    type = SelectField('Typ', choices=[
        ('jasper', "Objektblatt"),
        ('info', "Info Template"),
        ('qgis', "QGIS Drucklayout")
    ], default='jasper')
    jasper_file = FileField(
        'JasperReports Report', description="JasperReports Report auswählen"
    )
    info_file = FileField(
        'Template',
        description="HTML Template auswählen"
        "<br/><br/>Es kann ein beliebiges HTML Fragment, ohne "
        "<code>&lt;body></code>, <code>&lt;head></code>, "
        "<code>&lt;script></code>-Tags, eingesetzt werden. "
        "Inline-Styles sind möglich, ansonsten wird das CSS der "
        "Viewer-Applikation verwendet. "
        "<br/><br/>Feature Attribute können in der Form "
        "<code>{{ feature.title }}</code> eingefügt werden."
    )
    qgis_file = FileField(
        'QGIS Drucklayout',
        description="QPT oder ZIP mit QPT und Bildern auswählen"
    )

    default_format = SelectField('Default-Format', choices=[
        ('', ""),
        ('pdf', "pdf"),
        ('html', "html"),
        ('csv', "csv"),
        ('xls', "xls"),
        ('xlsx', "xlsx")
    ], default='')
    data_products = FieldList(FormField(DataProductForm))
    data_product = SelectField(
        'Verwendete DataProducts', coerce=int, validators=[Optional()]
    )
    # NOTE: use 'datasets' as field name to avoid conflict with
    #       'data_sets' from TemplateJasper model
    datasets = FieldList(FormField(DataSetForm))
    data_set = SelectField(
        'Verwendete DataSets', coerce=int, validators=[Optional()]
    )

    info_type = RadioField('', choices=[
        ('sql', 'DB Query'),
        ('module', 'Modul'),
        ('wms', 'WMS')
    ], default='wms')
    info_sql = TextAreaField(
        'SQL Query',
        description="Bei der Info-Abfrage werden u.a. folgende Werte übergeben:"
        "<br/>* <code>:x</code>: X Koordinate</li>"
        "<br/>* <code>:y</code>: Y Koordinate</li>"
        "<br/>* <code>:srid</code>: SRID der Koordinaten"
        "<br/>* <code>:resolution</code>: Auflösung in Meter pro Pixel"
        "<br/>* <code>:FI_POINT_TOLERANCE</code>: Toleranz in Pixeln für Punkte"
        "<br/>* <code>:FI_LINE_TOLERANCE</code>: Toleranz in Pixeln für Linien"
        "<br/>* <code>:FI_POLYGON_TOLERANCE</code>: Toleranz in Pixeln für Polygone"
        "<br/>* <code>:feature_count</code>: Maximale Anzahl Features"
        "<br/><br/>"
        "Die Feature-ID muss als <code>_fid_</code> und die WKT Geometrie "
        "als <code>wkt_geom</code> zurückgegeben werden. "
        "<br/><br/>z.B. <code>SELECT ogc_fid as _fid_, zone, ..., "
        "ST_AsText(wkb_geometry) as wkt_geom FROM schema.table "
        "WHERE ST_Intersects(wkb_geometry, "
        "ST_GeomFromText('POINT(:x :y)', :srid)) LIMIT 5;</code>",
        validators=[Optional()]
    )
    info_module = StringField(
        'Modul', description="Modulname des Custom Service",
        validators=[Optional()]
    )

    permissions = FieldList(FormField(PermissionForm))
    role = SelectField('Rolle', coerce=int, validators=[Optional()])

    submit = SubmitField('Speichern')

    def __init__(self, config_models, **kwargs):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models
        self.TemplateJasper = self.config_models.model('template_jasper')
        self.TemplateInfo = self.config_models.model('template_info')
        self.TemplateQGIS = self.config_models.model('template_qgis')

        # store any provided user object
        self.obj = kwargs.get('obj')

        super(TemplateForm, self).__init__(**kwargs)

    def validate_name(self, field):
        """Validate uniqueness of template name per type"""
        if self.type.data == 'jasper':
            template_model = self.TemplateJasper
            template_desc = "Objektblatt"
        elif self.type.data == 'info':
            template_model = self.TemplateInfo
            template_desc = "Info Template"
        elif self.type.data == 'qgis':
            template_model = self.TemplateQGIS
            template_desc = "QGIS Drucklayout"

        session = self.config_models.session()
        # check if template name of this type exists
        query = session.query(template_model).filter_by(name=field.data)
        if self.obj:
            # ignore current template
            query = query.filter(template_model.gdi_oid != self.obj.gdi_oid)
        template = query.first()
        session.close()

        if template is not None:
            raise ValidationError(
                'Ein %s mit diesem Namen ist bereits vorhanden' % template_desc
            )

    def validate_jasper_file(self, field):
        """Validate JasperReports file upload."""
        if self.type.data == 'jasper':
            if isinstance(field.data, FileStorage):
                if field.data.filename:
                    # check file extension
                    html_pattern = re.compile("^[^\/\\\\]+\.(jrxml|zip)$")
                    if not html_pattern.match(field.data.filename):
                        raise ValidationError(
                            'Datei ist kein JasperReports Report und kein ZIP'
                        )

    def validate_info_file(self, field):
        """Validate info HTML file upload."""
        if self.type.data == 'info':
            if isinstance(field.data, FileStorage):
                if field.data.filename:
                    # check file extension
                    html_pattern = re.compile("^[^\/\\\\]+\.html$")
                    if not html_pattern.match(field.data.filename):
                        raise ValidationError('Datei ist kein HTML')

    def validate_qgis_file(self, field):
        """Validate QPT file upload."""
        if self.type.data == 'qgis':
            if isinstance(field.data, FileStorage):
                if field.data.filename:
                    # check file extension
                    ext_pattern = re.compile("^[^\/\\\\]+\.(qpt|zip)$")
                    if not ext_pattern.match(field.data.filename):
                        raise ValidationError('Datei ist kein QPT oder ZIP')
