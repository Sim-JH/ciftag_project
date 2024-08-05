import logging
import os
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

from ciftag.exceptions import CIFTAGException

log = logging.getLogger(__name__)
base_dir = os.path.dirname(__file__)
template_dir = os.path.join(base_dir, 'config_templates')
CIFTAG_HOME: Optional[Path] = None
CIFTAG_CONFIG: Optional[Path] = None


class CiftagConfigParser(ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, section, key, **kwargs):
        try:
            return super().get(section, key, **kwargs)
        except Exception:
            raise CIFTAGException(
                f'section/key [{section}/{key}] not found in config'
            )

    def getboolean(self, section, key) -> bool:
        val = str(self.get(section, key)).lower().strip()
        if val in ['true', 'yes']:
            return True
        elif val in ['false', 'no']:
            return False
        else:
            raise CIFTAGException('Not a boolean')

    def getint(self, section, key) -> int:
        return int(self.get(section, key))


if "CIFTAG_HOME" not in os.environ:
    CIFTAG_HOME = Path('/src/module')
else:
    CIFTAG_HOME = Path(os.environ['CIFTAG_HOME'])

# product/dev/test
if "CIFTAG_CONFIG" not in os.environ:
    CIFTAG_CONFIG = CIFTAG_HOME / "ciftag_product.cfg"
else:
    CIFTAG_CONFIG = Path(os.environ['CIFTAG_CONFIG'])  # docker-compose 시, -var로 전달받도록

conf = CiftagConfigParser()
