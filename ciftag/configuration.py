import os
from configparser import ConfigParser
from pathlib import Path
from typing import Optional

from ciftag.exceptions import CiftagException

base_dir = os.path.dirname(__file__)
template_dir = os.path.join(base_dir, 'config_templates')
CIFTAG_HOME: Optional[Path] = None
CIFTAG_RAW: Optional[Path] = None
CIFTAG_CONFIG: Optional[Path] = None


def load_config_str(file_name: str) -> str:
    file_path = os.path.join(template_dir, file_name)

    with open(file_path) as f:
        data = f.read()

    return data


class CiftagConfigParser(ConfigParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get(self, section, key, **kwargs):
        try:
            return super().get(section, key, **kwargs)
        except Exception:
            raise CiftagException(
                f'section/key [{section}/{key}] not found in config'
            )

    def getboolean(self, section, key) -> bool:
        val = str(self.get(section, key)).lower().strip()
        if val in ['true', 'yes']:
            return True
        elif val in ['false', 'no']:
            return False
        else:
            raise CiftagException('Not a boolean')

    def getint(self, section, key) -> int:
        return int(self.get(section, key))


if "CIFTAG_HOME" not in os.environ:
    os.environ['CIFTAG_HOME'] = "/src/module"

CIFTAG_HOME = Path(os.environ['CIFTAG_HOME'])
CIFTAG_RAW = Path("/datadrive")

# product/dev/test
if "SERVER_TYPE" not in os.environ:
    CIFTAG_CONFIG = CIFTAG_HOME / "ciftag_product.cfg"
else:
    CIFTAG_CONFIG = CIFTAG_HOME / f"ciftag_{os.environ['SERVER_TYPE']}.cfg"

if not CIFTAG_CONFIG.is_file() or CIFTAG_CONFIG.stat().st_size == 0:
    """
    1. config_templates 내부 cfg 파일을 컨테이너에서 일회용으로 사용하도록 생성 (수정 방지)
    2. cfg 파일의 플레이스 홀더들을 현재 local 변수들로 변환
    """
    print(f"Creating new config file in: {CIFTAG_CONFIG}")
    config_str = load_config_str(CIFTAG_CONFIG.name)

    with open(CIFTAG_CONFIG, "w") as f:
        f.write(config_str.format(**locals()))

conf = CiftagConfigParser()
