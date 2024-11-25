# import re
# from datetime import date, timedelta
# from datetime import datetime
# import os
# import time
# import pandas as pd
# import boto3
# import pyarrow as pa
# import pyarrow.parquet as pq
# import io
# import json
# from subprocess import check_output
#
# from app.core.config import settings
# import app.utils.logger as logger
#
#
# class S3Manger:
#     def __init__(self) -> None:
#         self.s3_uri = settings.S3_URI
#         self.s3_uri_logistics = settings.S3_URI_LOGISTICS
#         self.s3_uri_pos = settings.S3_URI_POS
#         self.s3_uri_at = settings.S3_URI_AT
#         self.s3_uri_platform = settings.S3_URI_PLATFORM
#
#         self.s3_client = boto3.client(
#             "s3",
#             aws_access_key_id=settings.S3_KEY,
#             aws_secret_access_key=settings.S3_SECRET,
#             region_name="ap-northeast-2",
#         )
#
#     def __str__(self) -> str:
#         return f"using s3 bucket"
#
#     # def getList(self):
#     #     response = self.s3_client.list_objects_v2(
#     #         Bucket=self.s3_uri)
#
#     #     for content in response.get('Contents', []):
#     #         print(content['Key'])
#
#     def getListWithUrl(self, url):
#         lists = []
#         paginator = self.s3_client.get_paginator("list_objects_v2")
#         pages = paginator.paginate(Bucket=self.s3_uri, Prefix=url)
#
#         for page in pages:
#             for object in page["Contents"]:
#                 lists.append(object["Key"].replace(f"{url}/", ""))
#
#         return lists
#
#     def getUri(self, key_name):
#         if key_name[0:3] == "at/":
#             s3_uri = self.s3_uri_at
#         else:
#             key_name_lower = key_name.split("/")[0][-3:].lower()
#             if "src" in key_name_lower or "gis" in key_name_lower:
#                 s3_uri = self.s3_uri_logistics
#             elif "pos" in key_name_lower or "erp" in key_name_lower:
#                 s3_uri = self.s3_uri_pos
#             elif "ver" in key_name_lower:
#                 s3_uri = self.s3_uri_platform
#             else:
#                 s3_uri = self.s3_uri
#         return s3_uri
#
#     def getKeyName(self, keyName):
#         if keyName[0:3] == "at/":
#             keyName = keyName.replace("at/", "")
#
#         return keyName
#
#     def readData(self, keyName):
#         obj = self.s3_client.get_object(
#             Bucket=self.getUri(keyName), Key=self.getKeyName(keyName)
#         )
#         return pd.read_parquet(io.BytesIO(obj["Body"].read()))
#
#     def readDataLog(self, keyName):
#         obj = self.s3_client.get_object(
#             Bucket=self.getUri(keyName), Key=self.getKeyName(keyName)
#         )
#         return pd.read_csv(io.BytesIO(obj["Body"].read()))
#
#     # S3파일 덤프
#     def dump(self, df, keyName, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#
#         retry = 1
#         while retry <= 5:
#             try:
#                 keyName = keyName.replace("./logs/", "")
#                 logs.log_data(f"----> S3 파일 저장 : {keyName}")
#
#                 table = pa.Table.from_pandas(df, nthreads=1)
#                 writer = pa.BufferOutputStream()
#                 pq.write_table(table, writer)
#                 body = bytes(writer.getvalue())
#
#                 self.s3_client.put_object(
#                     Body=body, Bucket=self.getUri(keyName), Key=self.getKeyName(keyName)
#                 )
#                 break
#             except Exception as e:
#                 logs.log_data(f"----> S3 파일 저장 Error {retry} : {keyName} {e}", "error")
#                 time.sleep(10)
#                 retry += 1
#
#             if retry > 5:
#                 return False
#
#         return True
#
#     def dump_image(self, url, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#
#         retry = 1
#         while retry <= 5:
#             try:
#                 if os.path.exists(url):
#                     data = open(url, "rb")
#                     keyName = url.replace("./app/", "").replace("-", "/")
#
#                     logs.log_data(f"----> S3 파일 저장 : {keyName}")
#                     self.s3_client.put_object(
#                         Body=data,
#                         Bucket=self.getUri(keyName),
#                         Key=self.getKeyName(keyName),
#                     )
#                 else:
#                     logs.log_data(f"----> S3 파일 저장 실패 : {url} 없음")
#
#                 break
#             except Exception as e:
#                 logs.log_data(f"----> S3 파일 저장 Error {retry} : {keyName} {e}", "error")
#                 time.sleep(10)
#                 retry += 1
#
#             if retry > 5:
#                 return False
#
#         return True
#
#     # S3파일 덤프
#     def dump_url(self, body, keyName, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#
#         retry = 1
#         while retry <= 5:
#             try:
#                 logs.log_data(f"----> S3 파일 저장 : {keyName}")
#                 self.s3_client.put_object(
#                     Body=body, Bucket=self.getUri(keyName), Key=self.getKeyName(keyName)
#                 )
#                 break
#             except Exception as e:
#                 logs.log_data(f"----> S3 파일 저장 Error {retry} : {keyName} {e}", "error")
#                 time.sleep(10)
#                 retry += 1
#
#             if retry > 5:
#                 return False
#
#         return True
#
#     def dump_json(self, key, obj, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#
#         retry = 1
#         while retry <= 5:
#             try:
#                 self.s3_client.put_object(
#                     Bucket=self.s3_uri,
#                     Key=key,
#                     Body=json.dumps(obj, default=lambda o: o.__dict__, ensure_ascii=False),
#                 )
#                 break
#             except Exception as e:
#                 logs.log_data(f"----> S3 파일 저장 Error {retry} : {keyName} {e}", "error")
#                 time.sleep(10)
#                 retry += 1
#
#             if retry > 5:
#                 return False
#
#         return True
#     def delete_url(self, keyName, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#
#         retry = 1
#         while retry <= 5:
#             try:
#                 logs.log_data(f"----> S3 파일 삭제 : {keyName}")
#                 self.s3_client.delete_object(
#                     Bucket=self.getUri(keyName), Key=self.getKeyName(keyName)
#                 )
#                 break
#             except Exception as e:
#                 logs.log_data(f"----> S3 파일 저장 Error {retry} : {keyName} {e}", "error")
#                 time.sleep(10)
#                 retry += 1
#
#             if retry > 5:
#                 return False
#
#         return True
#
#     def read_csv(self, keyName):
#         obj = self.s3_client.get_object(
#             Bucket=self.getUri(keyName),
#             Key=keyName,
#         )
#         df = pd.read_csv(io.BytesIO(obj["Body"].read()))
#         return df
#
#     def get_today_scrap_order_apps(self, process_type, date_path, log_dir=None, log_name=None):
#         logs = logger.Logger(log_dir, log_name)
#         try:
#             paginator = self.s3_client.get_paginator("list_objects_v2")
#             prefix = f"Baemin/bae_check_rank_rivals/{process_type}/{date_path}"
#
#             logs.log_data(
#                 f"[get_today_scrap_order_apps] prefix: {prefix}",
#                 'info',
#                 'matzip'
#             )
#
#             page_iterator = paginator.paginate(Bucket=self.s3_uri, Prefix=prefix)
#             # response = self.s3_client.list_objects_v2(Bucket=self.s3_uri, Prefix=prefix)
#
#             _list = []
#             for page in page_iterator:
#                 # list += [keys['Key'].split('/')[-1].split('.json')[0] for keys in page['Contents']]
#                 if "Contents" not in page:
#                     continue
#                 for keys in page["Contents"]:
#                     if ".json" in keys["Key"]:
#                         _list.append(
#                             [keys["Key"].split("/")[-1].split(".json")[0], keys["Size"]]
#                         )
#             return _list
#         except Exception as e:
#             logs.log_data(
#                 f"get today scrap order app: {e}",
#                 'error',
#                 'matzip'
#             )
#
#             return []
