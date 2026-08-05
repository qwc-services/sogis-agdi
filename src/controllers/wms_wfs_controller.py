from flask import flash, json, redirect, render_template, url_for
from sqlalchemy.exc import IntegrityError, InternalError
from wtforms import ValidationError

from forms import WmsWfsForm


class WmsWfsController:
    """Controller for WMS/WFS GUI

    Update WMS/WFS metadata in wms_wfs.
    """

    def __init__(self, app, config_models, db_engine):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param DatabaseEngine db_engine: Database engine with DB connections
        """
        self.resource_name = "WMS/WFS"
        self.base_route = 'wms_wfs'
        self.endpoint_suffix = 'wms_wfs'
        self.templates_dir = 'wms_wfs'
        self.logger = app.logger
        self.config_models = config_models

        self.WmsWfs = self.config_models.model('wms_wfs')

        # add custom routes
        base_route = self.base_route
        suffix = self.endpoint_suffix
        # edit form
        app.add_url_rule(
            '/%s' % base_route,
            base_route, self.edit, methods=['GET']
        )
        # update
        app.add_url_rule(
            '/%s' % base_route, 'update_%s' % suffix, self.update,
            methods=['PUT', 'POST']
        )

    def edit(self):
        """Show edit form."""
        # get first WMS
        session = self.session()
        query = session.query(self.WmsWfs).filter_by(ows_type="WMS")
        wms_wfs = query.first()
        session.close()

        if wms_wfs is None:
            flash('Keine WMS/WFS Einträge vorhanden', 'error')

        template = '%s/form.html' % self.templates_dir
        form = self.create_form(wms_wfs, True)
        title = self.resource_name
        action = url_for('update_%s' % self.endpoint_suffix)
        return render_template(
            template, title=title, form=form, action=action, method='PUT'
        )

    def update(self):
        """Update WMS/WFS metadata."""
        # get first WMS
        session = self.session()
        query = session.query(self.WmsWfs).filter_by(ows_type="WMS")
        wms_wfs = query.first()

        if wms_wfs is not None:
            form = self.create_form(wms_wfs)
            if form.validate_on_submit():
                try:
                    # update and commit resources
                    self.update_resources(form, session)
                    session.commit()
                    session.close()

                    flash('%s wurde aktualisiert.' % self.resource_name,
                          'success')

                    # show edit form with QGSWriter log
                    template = '%s/form.html' % self.templates_dir
                    title = self.resource_name
                    action = url_for('update_%s' % self.endpoint_suffix)
                    return render_template(
                        template, title=title,
                        form=form, action=action, method='PUT'
                    )
                except InternalError as e:
                    flash('InternalError: %s' % e.orig, 'error')
                except IntegrityError as e:
                    flash('IntegrityError: %s' % e.orig, 'error')
                except ValidationError as e:
                    flash('%s konnte nicht gespeichert werden.' %
                          self.resource_name, 'warning')
                except Exception as e:
                    self.logger.error(e)
                    flash('Exception: %s' % e, 'error')
            else:
                flash('%s konnte nicht gespeichert werden.' %
                      self.resource_name, 'warning')

            session.close()

            # show validation errors
            template = '%s/form.html' % self.templates_dir
            title = self.resource_name
            action = url_for('update_%s' % self.endpoint_suffix)
            return render_template(
                template, title=title, form=form, action=action, method='PUT'
            )
        else:
            # resource not found
            session.close()
            flash('Keine WMS/WFS Einträge vorhanden', 'error')
            return redirect(url_for(self.base_route))

    def create_form(self, wms_wfs, edit_form=False):
        """Return form for editing WMS/WFS.

        :param object resource: wms_wfs object
        :param bool edit_form: Set if edit form
        """
        form = WmsWfsForm(obj=wms_wfs)

        if edit_form and wms_wfs and wms_wfs.ows_metadata:
            # override form fields with resource values on edit
            try:
                # load JSON from ows_metadata
                ows_metadata = json.loads(wms_wfs.ows_metadata)

                form.service_title.data = ows_metadata.get('service_title')
                form.service_abstract.data = \
                    ows_metadata.get('service_abstract')
                form.keywords.data = ows_metadata.get('keywords')
                form.contact_person.data = ows_metadata.get('contact_person')
                form.contact_organization.data = \
                    ows_metadata.get('contact_organization')
                form.contact_position.data = \
                    ows_metadata.get('contact_position')
                form.contact_phone.data = ows_metadata.get('contact_phone')
                form.contact_mail.data = ows_metadata.get('contact_mail')
                form.fees.data = ows_metadata.get('fees')
                form.access_constraints.data = \
                    ows_metadata.get('access_constraints')
                form.wms_root_title.data = ows_metadata.get('wms_root_title')
                form.crs_list.data = ows_metadata.get('crs_list')
                form.wms_extent.data = ows_metadata.get('wms_extent')
            except ValueError as e:
                msg = "Ungültiges JSON in wms_wfs.ows_metadata: %s" % e
                self.logger.error(msg)
                flash(msg, 'error')

        return form

    def update_resources(self, form, session):
        """Update WMS/WFS records in DB.

        :param FlaskForm form: Form for DataSource
        :param Session session: DB session
        """
        # create JSON from form data
        ows_metadata = json.dumps({
            'service_title': form.service_title.data,
            'service_abstract': form.service_abstract.data,
            'keywords': form.keywords.data,
            'contact_person': form.contact_person.data,
            'contact_organization': form.contact_organization.data,
            'contact_position': form.contact_position.data,
            'contact_phone': form.contact_phone.data,
            'contact_mail': form.contact_mail.data,
            'fees': form.fees.data,
            'access_constraints': form.access_constraints.data,
            'wms_root_title': form.wms_root_title.data,
            'crs_list': form.crs_list.data,
            'wms_extent': form.wms_extent.data
        }, ensure_ascii=False, indent=2)

        # update metadata of all wms_wfs records
        query = session.query(self.WmsWfs)
        for wms_wfs in query.all():
            wms_wfs.ows_metadata = ows_metadata

    def session(self):
        """Return new session for ConfigDB."""
        return self.config_models.session()
