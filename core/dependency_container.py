from typing import Dict, Any, Type, Optional, TypeVar, Callable
from config.app_config import AppConfig
from data.db import Database
from data.user_repository import UserRepository
from data.admin_repository import AdminRepository
from data.permission_repository import PermissionRepository
from data.blacklist_repository import BlacklistRepository
from service.user_service import UserService
from service.auth_service import AuthService
from service.security_service import SecurityService
from core.jwt_service import JWTService
from core.openvpn_manager import OpenVPNManager
from core.certificate_manager import CertificateManager
from core.service_manager import ServiceManager
from core.network_manager import NetworkManager
from core.config_generator import ConfigGenerator
T = TypeVar('T')

class DependencyContainer:
    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[[], Any]] = {}
        self._config: Optional[AppConfig] = None
    
    def register_config(self, config: AppConfig) -> None:
        self._config = config
        self._instances['config'] = config
    def register_singleton(self, name: str, factory: Callable[[], T]) -> None:
        self._factories[name] = factory
    
    def get(self, name: str) -> T:
        if name in self._instances:
            return self._instances[name]
        if name in self._factories:
            instance = self._factories[name]()
            self._instances[name] = instance
            return instance
        raise KeyError(f"Dependency '{name}' not registered")
    def register_core_dependencies(self) -> None:
        self.register_singleton('database', self._create_database)
        self.register_singleton('user_repository', self._create_user_repository)
        self.register_singleton('admin_repository', self._create_admin_repository)
        self.register_singleton('permission_repository', self._create_permission_repository)
        self.register_singleton('blacklist_repository', self._create_blacklist_repository)
        self.register_singleton('jwt_service', self._create_jwt_service)
        self.register_singleton('certificate_manager', self._create_certificate_manager)
        self.register_singleton('service_manager', self._create_service_manager)
        self.register_singleton('network_manager', self._create_network_manager)
        self.register_singleton('config_generator', self._create_config_generator)
        self.register_singleton('openvpn_manager', self._create_openvpn_manager)
    def register_service_dependencies(self) -> None:
        self.register_singleton('user_service', self._create_user_service)
        self.register_singleton('auth_service', self._create_auth_service)
        self.register_singleton('security_service', self._create_security_service)
    def _create_database(self) -> Database:
        return Database()
    def _create_user_repository(self) -> UserRepository:
        return UserRepository(self.get('database'))
    def _create_admin_repository(self) -> AdminRepository:
        return AdminRepository(self.get('database'))
    def _create_permission_repository(self) -> PermissionRepository:
        return PermissionRepository(self.get('database'))
    def _create_blacklist_repository(self) -> BlacklistRepository:
        return BlacklistRepository(self.get('database'))
    def _create_jwt_service(self) -> JWTService:
        return JWTService()
    def _create_certificate_manager(self) -> CertificateManager:
        return CertificateManager(self._config)
    def _create_service_manager(self) -> ServiceManager:
        return ServiceManager()
    def _create_network_manager(self) -> NetworkManager:
        return NetworkManager(self._config)
    def _create_config_generator(self) -> ConfigGenerator:
        return ConfigGenerator(self._config)
    def _create_openvpn_manager(self) -> OpenVPNManager:
        return OpenVPNManager(self._config)
    def _create_user_service(self) -> UserService:
        return UserService(
            self.get('user_repository'),
            self.get('openvpn_manager')
        )
    def _create_auth_service(self) -> AuthService:
        return AuthService(
            self.get('admin_repository'),
            self.get('permission_repository'),
            self.get('blacklist_repository'),
            self.get('jwt_service')
        )
    def _create_security_service(self) -> SecurityService:
        return SecurityService(
            self.get('user_repository'),
            self.get('blacklist_repository')
        )
    def cleanup(self) -> None:
        database = self._instances.get('database')
        if database:
            database.cleanup_pool()
        self._instances.clear()
_container = DependencyContainer()
def get_container() -> DependencyContainer:
    return _container
def initialize_container(config: AppConfig) -> None:
    container = get_container()
    container.register_config(config)
    container.register_core_dependencies()
    container.register_service_dependencies()
def get_service(service_name: str) -> Any:
    return get_container().get(service_name)
def cleanup_container() -> None:
    get_container().cleanup()
