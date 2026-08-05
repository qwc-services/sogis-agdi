import re

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import Optional


class WmsWfsForm(FlaskForm):
    service_title = StringField('ServiceTitle', validators=[Optional()])
    service_abstract = TextAreaField('ServiceAbstract', validators=[Optional()])
    keywords = StringField('Keywords', validators=[Optional()])
    contact_person = StringField('ContactPerson', validators=[Optional()])
    contact_organization = StringField(
        'ContactOrganization', validators=[Optional()]
    )
    contact_position = StringField('ContactPosition', validators=[Optional()])
    contact_phone = StringField('ContactPhone', validators=[Optional()])
    contact_mail = StringField('ContactMail', validators=[Optional()])
    fees = StringField('Fees', validators=[Optional()])
    access_constraints = StringField(
        'AccessConstraints', validators=[Optional()]
    )

    wms_root_title = StringField('Titel des Rootlayers', validators=[Optional()])
    crs_list = StringField(
        'Angebotene SRS',
        description="z.B. <code>EPSG:2056, EPSG:21781, EPSG:4326, "
                    "EPSG:3857</code>",
        validators=[Optional()]
    )
    wms_extent = StringField(
        'WMS Extent (LV95)',
        description="leer lassen für automatisch berechneten Extent aller "
                    "Layer",
        validators=[Optional()]
    )

    submit = SubmitField('Speichern')

    def validate_crs_list(self, field):
        if field.data:
            crs_pattern = re.compile("^EPSG:\d+$")
            crs_list = [crs.strip() for crs in field.data.split(',')]
            for crs in crs_list:
                if not crs_pattern.match(crs):
                    raise ValidationError('%s ist kein SRS' % crs)

    def validate_wms_extent(self, field):
        if field.data:
            try:
                valid = True
                wms_extent = [float(coord) for coord in field.data.split(',')]
                if len(wms_extent) != 4:
                    valid = False
                elif (wms_extent[0] > wms_extent[2] or
                      wms_extent[1] > wms_extent[3]):
                    valid = False
                if not valid:
                    raise ValidationError('Ungültiger WMS Extent.')
            except Exception as e:
                raise ValidationError('Ungültiger WMS Extent.')
