from flask import json
from sqlalchemy.sql import text as sql_text

from .controller import Controller
from forms import TransformationForm


class TransformationController(Controller):
    """Controller for Transformation GUI

    Manage transformation from GUI.
    """

    def __init__(self, app, config_models, db_engine):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        """
        super(TransformationController, self).__init__(
            "Transformation", 'transformation', 'transformation',
            'transformation', app, config_models
        )
        self.db_engine = db_engine

        self.Transformation = self.config_models.model('transformation')
        self.DataSet = self.config_models.model('data_set')

    def resource_pkey(self):
        """Return primary key column name."""
        return 'gdi_oid'

    def resources_for_index(self, session):
        """Return background layers list.

        :param Session session: DB session
        """
        return session.query(self.Transformation) \
            .order_by(self.Transformation.name).all()

    def form_for_new(self):
        """Return form for new background layer."""
        return self.create_form()

    def form_for_create(self):
        """Return form for creating Transformation."""
        return self.create_form()

    def create_resource(self, form, session):
        """Create new Transformation records in DB.

        :param FlaskForm form: Form for Transformation
        :param Session session: DB session
        """
        self.create_or_update_resources(None, form, session)

    def find_resource(self, id, session):
        """Find Transformation by ID.

        :param int id: Transformation ID
        :param Session session: DB session
        """
        return session.query(self.Transformation).filter_by(gdi_oid=id).first()

    def form_for_edit(self, resource):
        """Return form for editing Transformation.

        :param object resource: Transformation object
        """
        return self.create_form(resource, True)

    def form_for_update(self, resource):
        """Return form for updating Transformation.

        :param object resource: transformation object
        """
        return self.create_form(resource)

    def update_resource(self, resource, form, session):
        """Update existing Transformation records in DB.

        :param object resource: transformation object
        :param FlaskForm form: Form for Transformation
        :param Session session: DB session
        """
        self.create_or_update_resources(resource, form, session)

    def create_form(self, resource=None, edit_form=False):
        """Return form with fields loaded from DB.

        :param object resource: Optional transformation object
        :param bool edit_form: Set if edit form
        """
        form = TransformationForm(self.config_models, obj=resource)

        # load related resources from DB
        session = self.session()
        query = session.query(self.DataSet) \
            .order_by(self.DataSet.data_set_name) \
            .distinct(
                self.DataSet.gdi_oid_data_source, self.DataSet.data_set_name
            )
        data_sets = query.all()
        session.close()

        if edit_form:
            # add data sets for resource on edit

            # find current target data set in data set options
            gdi_oid_data_source = resource.data_set.gdi_oid_data_source
            data_set_name = resource.data_set.data_set_name
            for data_set in data_sets:
                if (
                    data_set.gdi_oid_data_source == gdi_oid_data_source
                    and data_set.data_set_name == data_set_name
                ):
                    # select target data set
                    form.target_data_set.data = data_set.gdi_oid
                    break

            # source data sets
            for data_set in resource.source_data_sets:
                form.data_sets.append_entry({
                    'data_set_id': data_set.gdi_oid,
                    'data_set_name': data_set.data_set_name
                })

        data_set_choices = [(0, "")] + [
            (d.gdi_oid, d.data_set_name) for d in data_sets
        ]

        # set choices for target data set select field
        form.target_data_set.choices = data_set_choices
        # set choices for source data set select field
        form.source_data_set.choices = data_set_choices

        return form

    def create_or_update_resources(self, resource, form, session):
        """Create or update Transformation records in DB.

        :param object resource: Optional transformation object
                                (None for create)
        :param FlaskForm form: Form for Transformation
        :param Session session: DB session
        """
        # find target data_set
        # NOTE: execute this query before creating new transformation
        #       to avoid validation errors
        data_set = self.find_data_set(int(form.target_data_set.data), session)

        if resource is None:
            # create new transformation
            transformation = self.Transformation()
            session.add(transformation)
            # create new target data_set
            target_data_set = self.DataSet()
            transformation.data_set = target_data_set
            session.add(target_data_set)
        else:
            # update existing transformation
            transformation = resource

        # update transformation
        transformation.name = form.name.data
        transformation.description = form.description.data

        # update target data_set
        target_data_set = transformation.data_set
        target_data_set.name = form.name.data
        target_data_set.description = form.description.data
        target_data_set.gdi_oid_data_source = data_set.gdi_oid_data_source
        target_data_set.data_set_name = data_set.data_set_name

        # update source data_sets
        self.update_source_data_sets(transformation, form, session)

    def destroy_resource(self, resource, session):
        """Delete existing Transformation records in DB.

        :param object resource: transformation object
        :param Session session: DB session
        """
        transformation = resource

        # remove source data_sets
        source_data_sets = [
            data_set for data_set in transformation.source_data_sets
        ]
        for source_data_set in source_data_sets:
            transformation.source_data_sets.remove(source_data_set)
            session.delete(source_data_set)

        # remove target data_set
        session.delete(transformation.data_set)

        # remove transformation
        session.delete(transformation)

    def find_data_set(self, data_set_id, session):
        """Get data_set with data_set_id from ConfigDB

        :param int data_set_id: data_set ID
        :param Session session: DB session
        """
        query = session.query(self.DataSet).filter_by(gdi_oid=data_set_id)
        data_set = query.first()

        return data_set

    def update_source_data_sets(self, transformation, form, session):
        """Add or remove source data sets for transformation.

        NOTE: create separate data_sets for each transformation.

        :param object transformation: transformation object
        :param FlaskForm form: Form for transformation
        :param Session session: DB session
        """
        target_data_set_name = transformation.data_set.data_set_name

        # lookup for source data_set of transformation
        source_data_sets = {}
        for data_set in transformation.source_data_sets:
            source_data_sets[data_set.gdi_oid] = data_set

        # update source data sets
        data_set_ids = []
        for data_set in form.data_sets:
            # get data_set from ConfigDB
            data_set_id = int(data_set.data['data_set_id'])
            data_set = self.find_data_set(data_set_id, session)

            if data_set is not None:
                if (
                    data_set.data_set_name == target_data_set_name
                    or data_set_id in data_set_ids
                ):
                    # skip target data set and duplicates
                    continue

                if data_set_id not in source_data_sets:
                    # copy data_set
                    new_data_set = self.DataSet()
                    new_data_set.data_set_name = data_set.data_set_name
                    new_data_set.gdi_oid_data_source = \
                        data_set.gdi_oid_data_source

                    # add source data_set to transformation
                    transformation.source_data_sets.append(new_data_set)
                    session.add(new_data_set)

                    # mark original id from form
                    data_set_ids.append(data_set.gdi_oid)

                    data_set = new_data_set
                # else update existing data_set

                # update data_set
                data_set.name = form.name.data
                data_set.description = form.description.data

                data_set_ids.append(data_set.gdi_oid)

        # remove removed source data sets
        for data_set in source_data_sets.values():
            if data_set.gdi_oid not in data_set_ids:
                # remove source data_set from transformation
                transformation.source_data_sets.remove(data_set)
                # remove data_set
                session.delete(data_set)
