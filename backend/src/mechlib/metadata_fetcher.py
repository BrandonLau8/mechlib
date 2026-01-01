import logging


logger = logging.getLogger(__name__)

class Metadata:
    def __init__(self, filename):
        self.filename: str = filename
        self.description: str | None = None
        self.brand: str | None = None
        self.materials: list | None = []
        self.process: list | None = []
        self.mechanism: str | None = None
        self.project: str | None = None
        self.person: str | None = None
        self.s3_url: str | None = None
        self.s3_uri: str | None = None

    def from_dict(self, data:dict):
        """Populate metadata from dict/JSON request"""
        if not data['filename'] and not data['description'] and data['person']:
            logger.warning('Incomplete Data')
            return None
        self.filename = data.get('filename')
        self.description = data.get('description')
        self.brand = data.get('brand')
        self.materials = data.get('materials', [])
        self.process = data.get('process', [])
        self.mechanism = data.get('mechanism')
        self.project = data.get('project')
        self.person = data.get('person')
        self.s3_url = None
        self.s3_uri = None

        logger.info('Metadata populated from dict/JSON')
        return self  # Enable method chaining


    def to_dict(self) -> dict:
        """Convert back to dict for processing"""
        logger.info('Metadata converted to dict')
        return {
            'filename': self.filename,
            'description': self.description,
            'brand': self.brand,
            'materials': self.materials,
            'process': self.process,
            'mechanism': self.mechanism,
            'project': self.project,
            'person': self.person,
            's3_url': self.s3_url,
            's3_uri': self.s3_uri
        }



    # def _validate_metadata(self) -> bool:
    #     nonnulls = ['description', 'person']
    #     metadata_keylist = list(metadata.keys())
    #     all_found = True
    #     for nonnull in nonnulls:
    #         if nonnull not in metadata_keylist:
    #             all_found = False
    #             break
    #
    #     if all_found:
    #         logger.info('Metadata Validated')
    #         return True
    #     else:
    #         logger.error('Metadata Not Validated')
    #         return False