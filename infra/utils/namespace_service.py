class NamespaceService:
    def __init__(self, namespace_name: str):
        self.namespace_name = namespace_name

    def namespace(self, resource_name: str, suffix: bool = False) -> str:
        """
        Namespaces a resource name with the instance's namespace.

        :param resource_name: The original name of the resource.
        :param suffix: Whether to append the namespace to the end of the resource name.
        :return: The namespaced resource name.
        """

        if suffix:
            return f"{resource_name}-{self.namespace_name}"

        return f"{self.namespace_name}-{resource_name}"
