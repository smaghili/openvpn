from abc import ABC, abstractmethod

class IBackupable(ABC):
    """
    Defines the contract for services that can be backed up and restored.
    Any protocol manager (like OpenVPNManager) that needs to be included in the
    system-wide backup must implement this interface.
    """

    @abstractmethod
    def get_backup_assets(self) -> list[str]:
        """
        Returns a list of absolute paths to files or directories
        that are essential for this service's state.
        
        Returns:
            list[str]: A list of file or directory paths.
        """
        pass

    @abstractmethod
    def pre_restore(self):
        """
        A hook to be called before the restore process begins.
        This is the appropriate place to stop services to prevent file conflicts.
        """
        pass

    @abstractmethod
    def post_restore(self):
        """
        A hook to be called after the restore process has successfully completed.
        This is the appropriate place to set file permissions and restart services.
        """
        pass
