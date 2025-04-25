from langchain_community.document_loaders.unstructured import UnstructuredFileLoader
from typing_extensions import TypeAlias
from pathlib import Path
from typing import List, Any

Element: TypeAlias = Any

class ICDLoader(UnstructuredFileLoader):
    def __init__(self, strategy="hi_res"):
        super().__init__(strategy=strategy)
    
    def _get_elements(self) -> List[Element]:
        from scrapers.custom_partition import partition
        
        if isinstance(self.file_path, list):
            elements: List[Element] = []
            for file in self.file_path:
                if isinstance(file, Path):
                    file = str(file)
                elements.extend(partition(filename=file, **self.unstructured_kwargs))
            return elements
        else:
            if isinstance(self.file_path, Path):
                self.file_path = str(self.file_path)
            return partition(filename=self.file_path, **self.unstructured_kwargs)