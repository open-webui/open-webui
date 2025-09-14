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
        state_name_mappings: Dict mapping env_name to desired state attribute name

    Example:
        >>> bootstrap = ConfigStateBootstrap(app)
        >>> bootstrap.bootstrap_config_state()
        >>> missing_configs = bootstrap.validate_config_completeness()
    """

    def __init__(self, app, state_name_mappings=None):
        """
        Initialize the bootstrap with a FastAPI application instance.

        Args:
            app: The FastAPI application instance that contains the state.config
                 object to be populated with configuration values.
            state_name_mappings: Optional dict mapping env_name to desired state
                                attribute name for cases where they differ.
        """
        self.app = app
        self.state_name_mappings = state_name_mappings or {
            # Misc
            "WEBUI_BANNERS": "BANNERS",
            # RAG
            "RAG_TOP_K": "TOP_K",
            "RAG_TOP_K_RERANKER": "TOP_K_RERANKERS",
            "RAG_RELEVANCE_THRESHOLD": "RELEVANCE_THRESHOLD",
            "RAG_HYBRID_BM25_WEIGHT": "HYBRID_BM25_WEIGHT",
            "RAG_ALLOWED_FILE_EXTENSIONS": "ALLOWED_FILE_EXTENSIONS",
            "RAG_FILE_MAX_SIZE": "FILE_MAX_SIZE",
            "RAG_FILE_MAX_COUNT": "FILE_MAX_COUNT",
            "RAG_TEXT_SPLITTER": "TEXT_SPLITTER",
            # STT
            "AUDIO_STT_ENGINE": "STT_ENGINE",
            "AUDIO_STT_MODEL": "STT_MODEL",
            "AUDIO_STT_SUPPORTED_CONTENT_TYPES": "STT_SUPPORTED_CONTENT_TYPES",
            "AUDIO_STT_OPENAI_API_BASE_URL": "STT_OPENAI_API_BASE_URL",
            "AUDIO_STT_OPENAI_API_KEY": "STT_OPENAI_API_KEY",
            # TTS
            "AUDIO_TTS_OPENAI_API_BASE_URL": "TTS_OPENAI_API_BASE_URL",
            "AUDIO_TTS_OPENAI_API_KEY": "TTS_OPENAI_API_KEY",
            "AUDIO_TTS_ENGINE": "TTS_ENGINE",
            "AUDIO_TTS_MODEL": "TTS_MODEL",
            "AUDIO_TTS_VOICE": "TTS_VOICE",
            "AUDIO_TTS_API_KEY": "TTS_API_KEY",
            "AUDIO_TTS_SPLIT_ON": "TTS_SPLIT_ON",
            "AUDIO_TTS_AZURE_SPEECH_REGION": "TTS_AZURE_SPEECH_REGION",
            "AUDIO_TTS_AZURE_SPEECH_BASE_URL": "TTS_AZURE_SPEECH_BASE_URL",
            "AUDIO_TTS_AZURE_SPEECH_OUTPUT_FORMAT": "TTS_AZURE_SPEECH_OUTPUT_FORMAT",
            # Variable name is different from env_name
            "LDAP_SEARCH_FILTER": "LDAP_SEARCH_FILTERS",
        }

    def bootstrap_config_state(self):
        """
        Bootstrap all app.state.config from PersistentConfig registry.

        This method iterates through all PersistentConfig items in the registry
        and sets them as attributes on app.state.config if they are not already
        present. This allows for non-destructive initialization that works
        alongside existing manual configuration assignments.

        For items with mappings in state_name_mappings, the mapped attribute name
        will be used instead of the env_name.

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
                # determine the attribute name to use on app.state.config
                state_attr_name = self.state_name_mappings.get(
                    config_item.env_name, config_item.env_name
                )

                # check if this config is already set to avoid overriding
                if hasattr(self.app.state.config, state_attr_name):
                    skipped_count += 1
                    log.debug(f"Skipping {state_attr_name} - already set")
                    continue

                # set the config using the appropriate attribute name
                setattr(self.app.state.config, state_attr_name, config_item)
                assigned_count += 1
                log.info(
                    f"Set app.state.config.{state_attr_name} from {config_item.env_name}"
                )

            except Exception as e:
                log.warning(
                    f"Failed to set app.state.config.{config_item.env_name}: {e}"
                )

        log.info(
            f"ConfigStateBootstrap: Set {assigned_count} configs, skipped {skipped_count} existing configs"
        )

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

    def get_state_attribute_mapping(self):
        """
        Get mapping of env_name to actual state attribute name.

        Returns:
            dict: Mapping showing what attribute name will be used on app.state.config
                 for each environment variable name.
        """
        mapping = {}
        for config in PERSISTENT_CONFIG_REGISTRY:
            state_attr_name = self.state_name_mappings.get(
                config.env_name, config.env_name
            )
            mapping[config.env_name] = state_attr_name
        return mapping
