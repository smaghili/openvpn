from abc import ABC, abstractmethod

class ProtocolManager(ABC):
    @abstractmethod
    def add_user(self, user, **kwargs):
        pass

    @abstractmethod
    def remove_user(self, user):
        pass

    @abstractmethod
    def generate_client_config(self, user):
        pass