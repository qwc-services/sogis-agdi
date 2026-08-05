import requests
from urllib.parse import urljoin

from flask import flash, json, redirect, render_template, url_for

from forms import PublishForm


class PublishController:
    """Controller for Publish page

    Publish WMS/WFS.
    """

    def __init__(self, app, config_models, service_config):
        """Constructor

        :param Flask app: Flask application
        :param ConfigModels config_models: Helper for ORM models
        :param func service_config: Helper method for reading service config
        """
        self.resource_name = "Publikation"
        self.base_route = 'publish'
        self.endpoint_suffix = 'publish'
        self.templates_dir = 'publish'
        self.logger = app.logger
        self.config_models = config_models
        self.service_config = service_config

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
        template = '%s/form.html' % self.templates_dir
        form = self.create_form(True)
        title = self.resource_name
        action = url_for('update_%s' % self.endpoint_suffix)
        return render_template(
            template, title=title, form=form, action=action, method='PUT'
        )

    def update(self):
        """Publish WMS/WFS."""
        form = self.create_form()
        try:
            # get URLs from service config
            config = self.service_urls()
            config_generator_url = config.get('config_generator_url')
            solr_update_url = config.get('solr_update_url')

            if form.service_configs.data:
                # generate service configs and permissions
                url = urljoin(config_generator_url, 'generate_configs')
                response = requests.post(url)
                if response.status_code == 200:
                    if 'error' not in response.json():
                        flash('Service Configs und Permissions wurden '
                              'aktualisiert.', 'success')
                    else:
                        flash('Fehler beim Aktualisieren der Service Configs '
                              'und Permissions', 'error')
                        flash(response.json()['error'], 'warning')
                else:
                    flash('ConfigGenerator request to %s failed: Status %d.'
                          % (url, response.status_code), 'error')
                    flash(response.text, 'warning')

            qgs_writer_log = []
            if form.wms_wfs.data:
                # update QGIS projects
                url = urljoin(config_generator_url, 'update_qgs')
                response = requests.post(url)
                if response.status_code == 200:
                    if 'error' not in response.json():
                        qgs_writer_log = response.json().get('log', [])
                        flash('QGIS Projekte wurden aktualisiert.', 'success')
                    else:
                        flash('Fehler beim Aktualisieren der QGIS Projekte',
                              'error')
                        flash(response.json()['error'], 'warning')
                else:
                    flash('ConfigGenerator request to %s failed: Status %d.'
                          % (url, response.status_code), 'error')
                    flash(response.text, 'warning')

            if form.solr_index.data:
                # update Solr Metadata index
                response = requests.get(solr_update_url)
                if response.status_code == 200:
                    flash('Aktualisierung Solr-Index gestartet. '
                          'Name des Aktualisierungsjobs: %s' % response.text,
                          'success')
                else:
                    flash('Aktualisierung Solr-Index Status %d.'
                          % response.status_code,
                          'error')
                    flash(response.text, 'warning')

            # show edit form with QGSWriter log
            template = '%s/form.html' % self.templates_dir
            title = self.resource_name
            action = url_for('update_%s' % self.endpoint_suffix)
            return render_template(
                template, title=title, qgs_writer_log=qgs_writer_log,
                form=form, action=action, method='PUT'
            )
        except Exception as e:
            self.logger.error(e)
            flash('Exception: %s' % e, 'error')

        # show messages
        template = '%s/form.html' % self.templates_dir
        title = self.resource_name
        action = url_for('update_%s' % self.endpoint_suffix)
        return render_template(
            template, title=title, form=form, action=action, method='PUT'
        )

    def create_form(self, edit_form=False):
        """Return form for publish page.

        :param bool edit_form: Set if edit form
        """
        solr_update_url = self.service_urls()['solr_update_url']
        form = PublishForm(meta={'solr_url': (solr_update_url != '')})

        return form

    def service_urls(self):
        """Return URLs for ConfigGenerator and Solr from service config."""
        # get URLs from service config
        config = self.service_config()
        config_generator_url = config.get(
            'config_generator_url', 'http://localhost:5032/'
        )
        solr_update_url = config.get(
            'solr_update_url',
            'http://localhost:8983/solr/gdi/dih_metadata?command=status'
        )

        return {
            'config_generator_url': config_generator_url,
            'solr_update_url': solr_update_url
        }
