from flask_wtf import FlaskForm
from wtforms import SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class ContactForm(FlaskForm):
    type = SelectField('Typ', choices=[
        ('person', "Person"),
        ('organisation', "Organisation")
    ])
    name = StringField('Name', validators=[DataRequired()])
    id_organisation = SelectField(
        'Organisation', coerce=int, validators=[Optional()]
    )

    function = SelectField('Funktion', choices=[
        ('GDI', "GDI"),
        ('Extern', "Extern"),
        ('Datenherr', "Datenherr")
    ], validators=[Optional()])
    email = StringField(
        'E-Mail',
        validators=[Email(message="Ungültige E-Mail Adresse"), Optional()]
    )
    phone = StringField('Telefon', validators=[Optional()])

    unit = StringField(
        'Organisationseinheit',
        description="z.B. Firma, Kanton, Departement, Amt, ...",
        validators=[Optional()]
    )
    abbreviation = StringField('Abkürzung', validators=[Optional()])

    street = StringField('Strasse', validators=[Optional()])
    house_no = StringField('Hausnummer', validators=[Optional()])
    zip = StringField('PLZ', validators=[Optional()])
    city = StringField('Ort', validators=[Optional()])
    country_code = StringField(
        'Ländercode',
        validators=[
            Length(max=3, message="Ländecode darf maximal 3 Zeichen enthalten"),
            Optional()
        ]
    )

    submit = SubmitField('Speichern')
