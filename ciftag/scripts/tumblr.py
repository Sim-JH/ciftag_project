from typing import Dict, Any

import ciftag.utils.logger as logger
from ciftag.scripts.core import save_sql

logs = logger.Logger(log_dir='sql')


def insert_tumb_result(args: Dict[str, Any]):
    sql = f"""INSERT INTO tumb_crawl_data (
                      tumb_pk,
                      run_on,
                      height,
                      width,
                      download, 
                      thumbnail_url,
                      image_url,
                      title,
                      detail_link
                  ) 
                  VALUES (
                      :tumb_pk, 
                      :run_on, 
                      :height, 
                      :width, 
                      :download,
                      :thumbnail_url,
                      :image_url,
                      :title,
                      :detail_link
                  ) 
              RETURNING id"""

    _, result_id = save_sql(sql, args=args, returning=True)

    return result_id

