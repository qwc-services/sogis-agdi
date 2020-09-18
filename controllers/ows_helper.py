class OWSHelper:
    """Helper class for managing WMS/WFS layers"""

    def __init__(self, config_models):
        """Constructor

        :param ConfigModels config_models: Helper for ORM models
        """
        self.config_models = config_models

        self.GroupLayer = self.config_models.model('group_layer')
        self.WmsWfs = self.config_models.model('wms_wfs')

    def layer_in_ows(self, ows_layer, ows_type):
        """Return whether OWS layer is in WMS/WFS.

        :param object ows_layer: ows_layer object
        :param str ows_type: OWS type (WMS or WFS)
        """
        session = self.config_models.session()
        group_layer = self.find_ows_group_layer_for_layer(
            ows_layer, ows_type, session
        )
        session.close()

        return group_layer is not None

    def update_ows(self, ows_layer, ows_type, add_layer, session):
        """Add or remove OWS layer to WMS/WFS root layer.

        :param object ows_layer: ows_layer object
        :param str ows_type: OWS type (WMS or WFS)
        :param bool add_layer: Add layer if true, remove if false
        :param Session session: DB session
        """
        root_layer = self.find_ows_root_layer(ows_type, session)
        if root_layer is not None:
            group_layer = self.find_ows_group_layer_for_layer(
                ows_layer, ows_type, session
            )
            if add_layer and group_layer is None:
                # get WMS/WFS layer count
                query = session.query(self.GroupLayer).filter_by(
                    gdi_oid_group_layer=root_layer.gdi_oid
                )
                layer_count = query.count()

                # append to WMS/WFS root layer by creating a new group_layer
                new_group_layer = self.GroupLayer(layer_order=layer_count, layer_active=True)
                new_group_layer.group = root_layer
                new_group_layer.sub_layer = ows_layer
                session.add(new_group_layer)
            elif not add_layer and group_layer is not None:
                # remove from WMS/WFS root layer
                session.delete(group_layer)

    def find_ows_root_layer(self, ows_type, session):
        """Return WMS/WFS root layer.

        :param str ows_type: OWS type (WMS or WFS)
        :param Session session: DB session
        """
        root_layer = None

        # get OWS root layer
        query = session.query(self.WmsWfs).filter_by(ows_type=ows_type)
        wms_wfs = query.first()
        if wms_wfs is not None:
            root_layer = wms_wfs.root_layer

        return root_layer

    def ows_root_layers(self, session):
        """Return all WMS/WFS root layers.

        :param Session session: DB session
        """
        root_layers = []

        # get OWS root layer
        query = session.query(self.WmsWfs)
        for wms_wfs in query.all():
            root_layers.append(wms_wfs.root_layer)

        return root_layers

    def find_ows_group_layer_for_layer(self, ows_layer, ows_type, session):
        """Return group_layer relation for OWS layer if attached to WMS/WFS.

        :param object ows_layer: ows_layer object
        :param str ows_type: OWS type (WMS or WFS)
        :param Session session: DB session
        """
        group_layer = None

        root_layer = self.find_ows_root_layer(ows_type, session)
        if root_layer is not None:
            # find existing group_layer for WMS/WFS
            query = session.query(self.GroupLayer).filter_by(
                gdi_oid_group_layer=root_layer.gdi_oid,
                gdi_oid_sub_layer=ows_layer.gdi_oid,
            )
            group_layer = query.first()

        return group_layer
