from open_webui.env import SRC_LOG_LEVELS
from .base import PERSISTENT_CONFIG_REGISTRY
import logging

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["CONFIG"])

class ConfigStateBootstrap:
    """
    Bootstrap app.state.config using PersistentConfig registry during application startup.

    This class provides a centralized way to initialize application state configuration
    by automatically setting all PersistentConfig items from the registry as attributes
    on app.state.config. It operates non-destructively, skipping any configs that are
    already set manually.

    The bootstrap process is designed to work alongside existing manual configuration
    assignments, allowing for gradual migration to the PersistentConfig system.

    Attributes:
        app: The FastAPI application instance with state to be configured

    Example:
        >>> bootstrap = ConfigStateBootstrap(app)
        >>> bootstrap.bootstrap_config_state()
        >>> missing_configs = bootstrap.validate_config_completeness()
    """

    def __init__(self, app):
        """
        Initialize the bootstrap with a FastAPI application instance.

        Args:
            app: The FastAPI application instance that contains the state.config
                 object to be populated with configuration values.
        """
        self.app = app

    def bootstrap_config_state(self):
        """
        Bootstrap all app.state.config from PersistentConfig registry.

        This method iterates through all PersistentConfig items in the registry
        and sets them as attributes on app.state.config if they are not already
        present. This allows for non-destructive initialization that works
        alongside existing manual configuration assignments.

        The method logs detailed information about the bootstrap process:
        - Number of configs successfully set
        - Number of configs skipped (already present)
        - Any errors encountered during the process

        Raises:
            No exceptions are raised. Errors are logged and the process continues
            to ensure application startup is not interrupted by config issues.

        Side Effects:
            - Sets attributes on app.state.config
            - Logs bootstrap progress and results
        """
        log.info("Bootstrapping app.state.config from PersistentConfig registry...")

        assigned_count = 0
        skipped_count = 0

        for config_item in PERSISTENT_CONFIG_REGISTRY:
            try:
                # Check if this config is already set to avoid overriding
                if hasattr(self.app.state.config, config_item.env_name):
                    skipped_count += 1
                    log.debug(f"Skipping {config_item.env_name} - already set")
                    continue

                # Use the env_name as the attribute name (e.g., "ENABLE_OLLAMA_API")
                setattr(self.app.state.config, config_item.env_name, config_item)
                assigned_count += 1
                log.debug(f"Set app.state.config.{config_item.env_name}")

            except Exception as e:
                log.warning(f"Failed to set app.state.config.{config_item.env_name}: {e}")

        log.info(f"ConfigStateBootstrap: Set {assigned_count} configs, skipped {skipped_count} existing configs")

    def get_registry_config_names(self):
        """
        Get list of all configuration names available in the PersistentConfig registry.

        This is a utility method for debugging and introspection. It returns all
        environment variable names that are defined in the PERSISTENT_CONFIG_REGISTRY
        and should be available for bootstrap.

        Returns:
            list[str]: A list of environment variable names (env_name) from all
                      PersistentConfig items in the registry.

        Example:
            >>> config_names = bootstrap.get_registry_config_names()
            >>> print(f"Available configs: {len(config_names)}")
            >>> print(f"First few: {config_names[:5]}")
        """
        return [config.env_name for config in PERSISTENT_CONFIG_REGISTRY]
