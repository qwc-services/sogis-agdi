from sqlalchemy.orm import joinedload

from .controller import Controller
from forms import ContactForm


class ContactsController(Controller):
    """Controller for Contact GUI

    Manage contact and related models from combined GUI.
    """

    def __init__(self, app, config_models):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(ContactsController, self).__init__(
            "Kontakt", 'contacts', 'contact', 'contacts', app, config_models
        )
        self.Contact = self.config_models.model('contact')
        self.Person = self.config_models.model('person')
        self.Organisation = self.config_models.model('organisation')

    def resources_for_index(self, session):
        """Return contacts list.

        :param Session session: DB session
        """
        query = session.query(self.Contact) \
            .order_by(self.Contact.type, self.Contact.name)
        # eager load relations
        query = query.options(joinedload(self.Contact.organisation))

        return query.all()

    def form_for_new(self):
        """Return form for new contact."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Contact."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Contact records in DB.

        :param FlaskForm form: Form for Contact
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Contact by ID.

        :param int id: Contact ID
        :param Session session: DB session
        """
        return session.query(self.Contact).filter_by(id=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Contact.

        :param object resource: Contact object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Contact.

        :param object resource: contact object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Contact records in DB.

        :param object resource: contact object
        :param FlaskForm form: Form for Contact
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional contact object
        :param bool edit_form: Set if edit form
        """
        form = ContactForm(obj=resource)

        if edit_form:
            # override form fields with resource values on edit
            form.id_organisation.data = resource.id_organisation
            if resource.type == 'person':
                form.function.data = resource.function
                form.email.data = resource.email
                form.phone.data = resource.phone
            elif resource.type == 'organisation':
                form.unit.data = resource.unit
                form.abbreviation.data = resource.abbreviation

        # load related resources from DB
        session = self.session()
        query = session.query(self.Organisation) \
            .order_by(self.Organisation.name)

        if resource is not None and resource.type == 'organisation':
            # skip organisation itself and member organisations
            member_ids = []
            self.collect_member_organisation_ids(resource, member_ids)
            if member_ids:
                query = query.filter(~self.Organisation.id.in_(member_ids))

        organisations = query.all()
        session.close()

        # set choices for organisation select field
        form.id_organisation.choices = [(0, "")] + [
            (o.id, o.abbreviation or o.name) for o in organisations
        ]

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Contact records in DB.

        :param object resource: Optional contact object
                                (None for create)
        :param FlaskForm form: Form for Contact
        :param Session session: DB session
        """
        if resource is None:
            # create new contact
            if form.type.data == 'person':
                contact = self.Person()
            elif form.type.data == 'organisation':
                contact = self.Organisation()
            else:
                contact = self.Contact()
            session.add(contact)
        else:
            # update existing contact
            contact = resource

        # update contact
        contact.name = form.name.data
        contact.street = form.street.data
        contact.house_no = form.house_no.data
        contact.zip = form.zip.data
        contact.city = form.city.data
        contact.country_code = form.country_code.data

        if form.id_organisation.data > 0:
            contact.id_organisation = form.id_organisation.data
        else:
            contact.id_organisation = None

        # type specific fields
        if form.type.data == 'person':
            contact.function = form.function.data
            contact.email = form.email.data
            contact.phone = form.phone.data
        elif form.type.data == 'organisation':
            contact.unit = form.unit.data
            contact.abbreviation = form.abbreviation.data

    def collect_member_organisation_ids(self, contact, member_ids):
        """Recursively collect member organisation IDs for an organisation.

        :param obj contact: Organisation or Person object
        :param list[int] member_ids: List of collected member organisation IDs
        """
        if contact.type == 'organisation':
            # add organisation ID
            member_ids.append(contact.id)

            # recursively collect members
            for member in contact.members:
                self.collect_member_organisation_ids(member, member_ids)
