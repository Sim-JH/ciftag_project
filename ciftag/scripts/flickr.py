from typing import Dict, Any

import ciftag.utils.logger as logger
from ciftag.scripts.core import save_sql

logs = logger.Logger(log_dir='sql')


def insert_flk_result(args: Dict[str, Any]):
    sql = f"""INSERT INTO flk_crawl_data (
                      flk_pk,
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
                      :flk_pk, 
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

