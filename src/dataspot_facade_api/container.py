from dependency_injector import containers, providers

from dataspot_facade_api.app_config import Configuration
from dataspot_facade_api.services.auth_service import DataspotAuthClient
from dataspot_facade_api.services.authorization_service import DatasetAuthorizationService
from dataspot_facade_api.services.dataset_service import DatasetService


class Container(containers.DeclarativeContainer):
    config: providers.Object[Configuration] = providers.Object(Configuration.from_env())

    dataspot_auth: providers.Singleton[DataspotAuthClient] = providers.Singleton(DataspotAuthClient)

    dataset_service: providers.Factory[DatasetService] = providers.Factory(
        DatasetService,
        config=config,
        dataspot_auth=dataspot_auth,
    )

    dataset_authorization_service: providers.Factory[DatasetAuthorizationService] = providers.Factory(
        DatasetAuthorizationService,
        config=config,
        dataspot_auth=dataspot_auth,
    )
