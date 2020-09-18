class PermissionsHelper:
    """Helper class for managing permissions"""

    # name of public iam.role
    PUBLIC_ROLE_NAME = 'public'

    def __init__(self, config_models):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models

        self.Role = self.config_models.model('role')
        self.ResourcePermission = self.config_models.model(
            'resource_permission'
        )

    def roles(self):
        """Return all roles."""
        # load roles from DB
        session = self.config_models.session()
        roles_query = session.query(self.Role).order_by(self.Role.name)
        roles = roles_query.all()
        session.close()

        return roles

    def resource_roles(self, gdi_oid):
        """Return permitted roles for a GDI resource.

        :param int gdi_oid: GDI resource ID
        """
        # get permitted roles for map from DB
        session = self.config_models.session()
        query = session.query(self.Role) \
            .join(self.Role.resource_permission_collection) \
            .filter(
                self.ResourcePermission.gdi_oid_resource == gdi_oid
            ) \
            .order_by(self.Role.name)
        roles = query.all()
        session.close()

        return roles

    def role(self, role_id):
        """Return Role by role ID.

        :param int id: role ID
        """
        # get Role from DB
        session = self.config_models.session()
        query = session.query(self.Role).filter_by(id=role_id)
        role = query.first()
        session.close()

        return role

    def public_role(self):
        """Return public Role."""
        # get Role from DB
        session = self.config_models.session()
        query = session.query(self.Role).filter_by(name=self.PUBLIC_ROLE_NAME)
        role = query.first()
        session.close()

        return role

    def update_resource_permission(self, gdi_resource_id, role_id, read, write,
                                   session):
        """Add or remove permission for a GDI resource.

        :param int gdi_resource_id: GDI resource ID
        :param int role_id: Role ID
        :param bool read: Readable permission
        :param bool write: Writable permission
        :param Session session: DB session
        """
        # get ResourcePermission from DB
        query = session.query(self.ResourcePermission) \
            .join(self.ResourcePermission.role) \
            .filter(self.ResourcePermission.id_role == role_id) \
            .filter(self.ResourcePermission.gdi_oid_resource == gdi_resource_id)
        permission = query.first()

        # get public role
        public_role = self.public_role()

        if read:
            # If GDI resource has at least read permissions, add/update existing permission recordo
            if not permission:
                permission = self.ResourcePermission()
            if public_role and public_role.id == role_id:
                # assign lower priority to public role
                permission.priority = 0
            else:
                # assign higher priority to non-public roles
                permission.priority = 1
            permission.write = write
            permission.id_role = role_id
            permission.gdi_oid_resource = gdi_resource_id
            session.add(permission)
        elif permission and not read:
            # Remove existing permission since GDI resources has no read permissions
            session.delete(permission)

    def remove_resource_permissions(self, gdi_resource_id, session):
        """Remove all permissions for a GDI resource.

        :param int gdi_resource_id: GDI resource ID
        :param Session session: DB session
        """
        query = session.query(self.ResourcePermission) \
            .filter(self.ResourcePermission.gdi_oid_resource == gdi_resource_id)
        query.delete()
