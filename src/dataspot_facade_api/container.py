from dependency_injector import containers, providers

from dataspot_facade_api.app_config import Configuration


class Container(containers.DeclarativeContainer):
    config: providers.Object[Configuration] = providers.Object(Configuration.from_env())
