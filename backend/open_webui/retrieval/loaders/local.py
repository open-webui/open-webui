from importlib import import_module
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.documents import Document


class TextLoader:
    def __init__(self, file_path, encoding=None):
        self.file_path = str(file_path)
        self.encoding = encoding

    def load(self) -> list[Document]:
        try:
            text = Path(self.file_path).read_text(encoding=self.encoding)
        except Exception as e:
            raise RuntimeError(f'Error loading {self.file_path}') from e
        return [
            Document(
                page_content=text,
                metadata={'source': self.file_path},
            )
        ]


class HTMLLoader(TextLoader):
    def load(self) -> list[Document]:
        with open(self.file_path, encoding=self.encoding) as file:
            soup = BeautifulSoup(file, 'lxml')
        return [
            Document(
                page_content=soup.get_text(),
                metadata={'source': self.file_path, 'title': str(soup.title.string) if soup.title else ''},
            )
        ]


class DocxLoader(TextLoader):
    def load(self) -> list[Document]:
        import docx2txt

        return [
            Document(
                page_content=docx2txt.process(Path(self.file_path).expanduser()),
                metadata={'source': self.file_path},
            )
        ]


class UnstructuredLoader:
    def __init__(self, file_path, file_format, mode='single', **kwargs):
        # Match the optional-package check; format dependencies are loaded when parsing.
        import_module('unstructured')
        self.file_path = file_path
        self.file_format = file_format
        self.mode = mode
        self.kwargs = kwargs

    def load(self) -> list[Document]:
        file_format = self.file_format
        if file_format in ('doc', 'ppt', 'pptx'):
            from unstructured.file_utils.filetype import detect_filetype

            legacy_format = 'doc' if file_format == 'doc' else 'ppt'
            try:
                import_module('magic')
            except ImportError:
                is_legacy = Path(self.file_path).suffix == f'.{legacy_format}'
            else:
                is_legacy = detect_filetype(self.file_path).name.lower() == legacy_format
            file_format = legacy_format if is_legacy else legacy_format + 'x'
        elif file_format == 'msg':
            from unstructured.file_utils.filetype import detect_filetype

            detected = detect_filetype(self.file_path).name
            if detected not in ('EML', 'MSG'):
                raise ValueError(f'Unsupported email file type: {detected}')
            file_format = 'email' if detected == 'EML' else 'msg'

        module = import_module(f'unstructured.partition.{file_format}')
        elements = getattr(module, f'partition_{file_format}')(filename=self.file_path, **self.kwargs)
        metadata = {'source': str(self.file_path)}
        if self.mode == 'elements':
            return [
                Document(
                    page_content=str(element),
                    metadata={
                        **metadata,
                        **element.metadata.to_dict(),
                        'category': element.category,
                        'element_id': element.id,
                    },
                )
                for element in elements
            ]
        return [Document(page_content='\n\n'.join(map(str, elements)), metadata=metadata)]


class DocumentIntelligenceLoader:
    def __init__(self, file_path, api_endpoint, api_key=None, azure_credential=None, api_model='prebuilt-layout'):
        if (api_key is None) == (azure_credential is None):
            raise ValueError('Provide exactly one of api_key or azure_credential.')
        self.file_path = file_path
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.azure_credential = azure_credential
        self.api_model = api_model

    def load(self) -> list[Document]:
        from azure.ai.documentintelligence import DocumentIntelligenceClient
        from azure.core.credentials import AzureKeyCredential

        credential = self.azure_credential if self.azure_credential is not None else AzureKeyCredential(self.api_key)
        with DocumentIntelligenceClient(self.api_endpoint, credential) as client, open(self.file_path, 'rb') as file:
            result = client.begin_analyze_document(
                self.api_model,
                body=file,
                content_type='application/octet-stream',
                output_content_format='markdown',
            ).result()
        return [Document(page_content=result.content, metadata=result.as_dict())]
