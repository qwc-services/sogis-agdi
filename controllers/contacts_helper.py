from sqlalchemy.orm import joinedload


class ContactsHelper:
    """Helper class for querying contacts"""

    ROLE_RESPONSIBLE = "Verantwortlicher"
    ROLE_DATA_OWNER = "Datenherr"
    ROLE_SUPPLIER = "Lieferant"

    def __init__(self, config_models, logger):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        :param Logger logger: Application logger
        """
        self.config_models = config_models
        self.logger = logger

        self.Contact = self.config_models.model('contact')
        self.Person = self.config_models.model('person')
        self.Organisation = self.config_models.model('organisation')
        self.ContactRole = self.config_models.model('contact_role')
        self.ResourceContact = self.config_models.model('resource_contact')

    def contact_choices(self):
        """Return choices for a contact select field."""
        choices = []

        session = self.config_models.session()

        # get contacts, organisations first
        query = session.query(self.Contact).order_by(self.Contact.type.desc())
        # order by organisation name then contact name
        query = query.outerjoin(self.Contact.organisation) \
            .order_by(self.Organisation.name, self.Contact.name)
        # eager load relations
        query = query.options(joinedload(self.Contact.organisation))

        # collect person IDs and names
        for contact in query.all():
            name = contact.name
            organisation = contact.organisation
            if organisation:
                name = "%s / %s" % (
                    contact.name, organisation.abbreviation or organisation.name
                )

            choices.append((contact.id, name))

        session.close()

        return choices

    def person_choices(self):
        """Return choices for a person select field."""
        choices = []

        session = self.config_models.session()

        # get persons
        query = session.query(self.Person)
        # order by organisation name then person name
        query = query.outerjoin(self.Person.organisation) \
            .order_by(self.Organisation.name, self.Person.name)
        # eager load relations
        query = query.options(joinedload(self.Person.organisation))

        # collect person IDs and names
        for person in query.all():
            name = person.name
            organisation = person.organisation
            if organisation:
                name = "%s / %s" % (
                    person.name, organisation.abbreviation or organisation.name
                )

            choices.append((person.id, name))

        session.close()

        return choices

    def resource_contact_id(self, gdi_resource_id, role_type):
        """Return assigned contact ID for a GDI resource and role.

        :param int gdi_resource_id: GDI resource ID
        :param str role_type: Contact role type
        """
        contact_id = None

        # find resource_contact
        session = self.config_models.session()
        resource_contact = self.resource_contact(
            gdi_resource_id, role_type, session
        )
        if resource_contact is not None:
            # get contact ID
            contact_id = resource_contact.id_contact
        session.close()

        return contact_id

    def resource_contact(self, gdi_resource_id, role_type, session):
        """Return resource_contact for a GDI resource and role.

        :param int gdi_resource_id: GDI resource ID
        :param str role_type: Contact role type
        :param Session session: DB session
        """
        resource_contact = None

        # find contact role
        role = self.role(role_type, session)
        if role is not None:
            # find resource_contact
            query = session.query(self.ResourceContact).filter_by(
                id_contact_role=role.id,
                gdi_oid_resource=gdi_resource_id
            )
            resource_contact = query.first()

        return resource_contact

    def update_resource_contact(self, gdi_resource_id, role_type, contact_id,
                                session):
        """Update resource_contact for a GDI resource

        NOTE: Creates new contact role if missing

        :param int gdi_resource_id: GDI resource ID
        :param str role_type: Contact role type
        :param int contact_id: Contact ID (set 0 to remove)
        :param Session session: DB session
        """
        # find existing resource_contact
        resource_contact = self.resource_contact(
            gdi_resource_id, role_type, session
        )
        if resource_contact is None:
            if contact_id > 0:
                # find contact role
                role = self.role(role_type, session)
                if role is None:
                    # create new contact role if missing
                    self.logger.info(
                        "Creating new contact role '%s'" % role_type
                    )
                    role = self.ContactRole(type=role_type)
                    session.add(role)
                    session.flush()

                # create new resource_contact
                resource_contact = self.ResourceContact(
                    id_contact_role=role.id,
                    id_contact=contact_id,
                    gdi_oid_resource=gdi_resource_id
                )
                session.add(resource_contact)
        else:
            if contact_id > 0:
                # update existing resource_contact
                resource_contact.id_contact = contact_id
            else:
                # remove existing resource_contact
                session.delete(resource_contact)

    def remove_resource_contacts(self, gdi_resource_id, session):
        """Remove all resource_contacts for a GDI resource.

        :param int gdi_resource_id: GDI resource ID
        :param Session session: DB session
        """
        query = session.query(self.ResourceContact).filter_by(
            gdi_oid_resource=gdi_resource_id
        )
        query.delete()

    def role(self, role_type, session):
        """Return contact_role by role type.

        :param str role_type: Contact role type
        :param Session session: DB session
        """
        # get contact_role from DB
        query = session.query(self.ContactRole).filter_by(type=role_type)
        role = query.first()

        return role
