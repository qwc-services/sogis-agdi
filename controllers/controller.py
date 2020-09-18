from flask import abort, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError, InternalError
from wtforms import ValidationError


class Controller:
    """Controller base class

    Add routes for specific controller and provide generic RESTful actions.
    """

    def __init__(self, resource_name, base_route, endpoint_suffix,
                 templates_dir, app, config_models):
        """Constructor

        :param str resource_name: Visible name of resource (e.g. 'Benutzer')
        :param str base_route: Base route for this controller (e.g. 'users')
        :param str endpoint_suffix: Suffix for route endpoints (e.g. 'user')
        :param str templates_dir: Subdir for resource templates (e.g. 'users')
        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        self.resource_name = resource_name
        self.base_route = base_route
        self.endpoint_suffix = endpoint_suffix
        self.templates_dir = templates_dir
        self.logger = app.logger
        self.config_models = config_models

        self.add_routes(app)

    def add_routes(self, app):
        """Add routes for this controller.

        :param Flask app: Flask application
        """
        base_route = self.base_route
        suffix = self.endpoint_suffix

        # index
        app.add_url_rule(
            '/%s' % base_route, base_route, self.index, methods=['GET']
        )
        # new
        app.add_url_rule(
            '/%s/new' % base_route, 'new_%s' % suffix, self.new, methods=['GET']
        )
        # create
        app.add_url_rule(
            '/%s' % base_route, 'create_%s' % suffix, self.create,
            methods=['POST']
        )
        # edit
        app.add_url_rule(
            '/%s/<int:id>/edit' % base_route, 'edit_%s' % suffix, self.edit,
            methods=['GET']
        )
        # update
        app.add_url_rule(
            '/%s/<int:id>' % base_route, 'update_%s' % suffix, self.update,
            methods=['PUT']
        )
        # delete
        app.add_url_rule(
            '/%s/<int:id>' % base_route, 'destroy_%s' % suffix, self.destroy,
            methods=['DELETE']
        )
        # update or delete
        app.add_url_rule(
            '/%s/<int:id>' % base_route, 'modify_%s' % suffix, self.modify,
            methods=['POST']
        )

    # index

    def resource_pkey(self):
        """Return primary key column name for resource table (default: 'id')"""
        return 'id'

    def resources_for_index(self, session):
        """Return resources list.

        Implement in subclass

        :param Session session: DB session
        """
        raise NotImplementedError

    def index(self):
        """Show resources list."""
        session = self.session()
        resources = self.resources_for_index(session)
        session.close()

        return render_template(
            '%s/index.html' % self.templates_dir, resources=resources,
            endpoint_suffix=self.endpoint_suffix, pkey=self.resource_pkey()
        )

    # new

    def form_for_new(self):
        """Return form for new resource.

        Implement in subclass
        """
        raise NotImplementedError

    def new(self):
        """Show new resource form."""
        template = '%s/form.html' % self.templates_dir
        form = self.form_for_new()
        title = "%s hinzufügen" % self.resource_name
        action = url_for('create_%s' % self.endpoint_suffix)

        return render_template(
            template, title=title, form=form, action=action, method='POST'
        )

    # create

    def form_for_create(self):
        """Return form for creating resource.

        Implement in subclass
        """
        raise NotImplementedError

    def create_resource(self, form, session):
        """Create new resource in DB.

        Implement in subclass

        :param FlaskForm form: Form for resource
        :param Session session: DB session
        """
        raise NotImplementedError

    def create(self):
        """Create new resource."""
        form = self.form_for_create()
        if form.validate_on_submit():
            try:
                # create and commit resource
                session = self.session()
                self.create_resource(form, session)
                session.commit()
                session.close()
                flash('%s wurde hinzugefügt.' % self.resource_name, 'success')

                return redirect(url_for(self.base_route))
            except InternalError as e:
                flash('InternalError: %s' % e.orig, 'error')
            except IntegrityError as e:
                flash('IntegrityError: %s' % e.orig, 'error')
            except ValidationError as e:
                flash('%s konnte nicht gespeichert werden.' %
                      self.resource_name, 'warning')
        else:
            flash('%s konnte nicht gespeichert werden.' % self.resource_name,
                  'warning')

        # show validation errors
        template = '%s/form.html' % self.templates_dir
        title = "%s hinzufügen" % self.resource_name
        action = url_for('create_%s' % self.endpoint_suffix)

        return render_template(
            template, title=title, form=form, action=action, method='POST'
        )

    # edit

    def find_resource(self, id, session):
        """Find resource by ID.

        Implement in subclass

        :param int id: Resource ID
        :param Session session: DB session
        """
        raise NotImplementedError

    def form_for_edit(self, resource):
        """Return form for editing resource.

        Implement in subclass

        :param object resource: Resource object
        """
        raise NotImplementedError

    def edit(self, id):
        """Show edit resource form.

        :param int id: Resource ID
        """
        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            template = '%s/form.html' % self.templates_dir
            form = self.form_for_edit(resource)
            session.close()
            title = "%s bearbeiten" % self.resource_name
            action = url_for('update_%s' % self.endpoint_suffix, id=id)

            return render_template(
                template, title=title, form=form, action=action, method='PUT'
            )
        else:
            # resource not found
            session.close()
            abort(404)

    # update

    def form_for_update(self, resource):
        """Return form for updating resource.

        Implement in subclass

        :param object resource: Resource object
        """
        raise NotImplementedError

    def update_resource(self, resource, form, session):
        """Update existing resource in DB.

        Implement in subclass

        :param object resource: Resource object
        :param FlaskForm form: Form for resource
        :param Session session: DB session
        """
        raise NotImplementedError

    def update(self, id):
        """Update existing resource.

        :param int id: Resource ID
        """
        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            form = self.form_for_update(resource)
            if form.validate_on_submit():
                try:
                    # update and commit resource
                    self.update_resource(resource, form, session)
                    session.commit()
                    session.close()
                    flash('%s wurde aktualisiert.' % self.resource_name,
                          'success')

                    return redirect(url_for(self.base_route))
                except InternalError as e:
                    flash('InternalError: %s' % e.orig, 'error')
                except IntegrityError as e:
                    flash('IntegrityError: %s' % e.orig, 'error')
                except ValidationError as e:
                    flash('%s konnte nicht gespeichert werden.' %
                          self.resource_name, 'warning')
            else:
                flash('%s konnte nicht gespeichert werden.' %
                      self.resource_name, 'warning')

            session.close()

            # show validation errors
            template = '%s/form.html' % self.templates_dir
            title = "%s bearbeiten" % self.resource_name
            action = url_for('update_%s' % self.endpoint_suffix, id=id)

            return render_template(
                template, title=title, form=form, action=action, method='PUT'
            )
        else:
            # resource not found
            session.close()
            abort(404)

    # destroy

    def destroy_resource(self, resource, session):
        """Delete existing resource in DB.

        :param object resource: Resource object
        :param Session session: DB session
        """
        session.delete(resource)

    def destroy(self, id):
        """Delete existing resource.

        :param int id: Resource ID
        """
        # find resource
        session = self.session()
        resource = self.find_resource(id, session)

        if resource is not None:
            try:
                # update and commit resource
                self.destroy_resource(resource, session)
                session.commit()
                flash('%s wurde entfernt.' % self.resource_name, 'success')
            except InternalError as e:
                flash('InternalError: %s' % e.orig, 'error')
            except IntegrityError as e:
                flash('IntegrityError: %s' % e.orig, 'error')

            session.close()

            return redirect(url_for(self.base_route))
        else:
            # resource not found
            session.close()
            abort(404)

    def modify(self, id):
        """Workaround for missing PUT and DELETE methods in HTML forms
        using hidden form parameter '_method'.
        """
        method = request.form.get('_method', '').upper()
        if method == 'PUT':
            return self.update(id)
        elif method == 'DELETE':
            return self.destroy(id)
        else:
            abort(405)

    def session(self):
        """Return new session for ConfigDB."""
        return self.config_models.session()

    def raise_validation_error(self, field, msg):
        """Raise ValidationError for a field.

        :param wtforms.fields.Field field: WTForms field
        :param str msg: Validation error message
        """
        error = ValidationError(msg)
        field.errors.append(error)
        raise error

    def update_collection(self, collection, subform, id_field, relation_model,
                          id_attr, session):
        """Helper to add or remove relations from a resource collection.

        :param object collection: Collection of resource relations
                                  (e.g. Group.user_collection)
        :param FieldList subform: Subform for relations (e.g. form.users)
        :param str id_field: ID field of subform (e.g. 'user_id')
        :param object relation_model: ConfigModel for relation (e.g. User)
        :param str id_attr: ID attribute of relation model (e.g. 'id')
        :param Session session: DB session
        """
        # lookup for relation of resource
        resource_relations = {}
        for relation in collection:
            resource_relations[relation.id] = relation

        # update relations
        relation_ids = []
        for relation in subform:
            # get relation from ConfigDB
            relation_id = int(relation.data[id_field])
            filter = {id_attr: relation_id}
            query = session.query(relation_model).filter_by(**filter)
            relation = query.first()

            if relation is not None:
                relation_ids.append(relation_id)
                if relation_id not in resource_relations:
                    # add relation to resource
                    collection.append(relation)

        # remove removed relations
        for relation in resource_relations.values():
            if relation.id not in relation_ids:
                # remove relation from resource
                collection.remove(relation)
