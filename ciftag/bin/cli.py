import subprocess
import sys
import time
import argparse

import sqlalchemy

import ciftag.utils.logger as logger
from ciftag.utils import bootstrap
from ciftag.configuration import conf


logs = logger.Logger(log_dir='CLI')


def initdb(args):
    """데이터베이스 초기화"""
    bootstrap.initdb(args.aws)


def restart_worker(args):
    subprocess.run(f'supervisorctl restart {args.worker}', shell=True, check=True)


def start_api_server(args):
    """API 서버 시작. 필요 시 데이터베이스 초기화도 수행"""
    import uvicorn
    from ciftag.web.app import create_app

    if args.initdb:
        print("Run API server with Init tables")
        # 1분간 6회에 걸쳐 접속 요청
        for cnt in range(6):
            try:
                # DB 생성 (테이블이 없을 경우에만 생성)
                bootstrap.initdb()
                break
            except sqlalchemy.exc.OperationalError as e:
                logs.log_data(f"Trying agains in 10 seconds... {cnt}")
                time.sleep(10)

    host = conf.get("web", "api_host")
    port = conf.get("web", "api_port")

    if args.develop:
        uvicorn.run('ciftag.web.app:create_app', host=host, port=int(port), reload=True)
    else:
        app = create_app(False)
        uvicorn.run(app, host=host, port=int(port))


def run_crawler(args):
    import ciftag.fargate.run as fargate_crawl
    if args.run_type == "test":
        container_start_time = time.time()
        while True:
            if int(time.time()) > int(container_start_time) + 3600:
                exit()
            time.sleep(600)
    else:
        fargate_crawl.runner(args.run_type, int(args.work_id))


def run_crawl_consumer(args):
    from ciftag.streams.crawler import (
        main_crawler,
        sub_crawler,
        aggregate_crawl
    )
    if args.consumer_type == "main":
        runner = main_crawler.MainCrawlConsumer()
    elif args.consumer_type == "sub":
        runner = sub_crawler.SubCrawlConsumer(task_type=args.task_type)
    elif args.consumer_type == "agt":
        runner = aggregate_crawl.AggregateConsumer()

    runner.run()


def run_download_consumer(args):
    if args.consumer_type == "img":
        from ciftag.streams.downloader import img_downloader
        runner = img_downloader.ImgDownloadConsumer()
    elif args.consumer_type == "filter":
        from ciftag.streams.downloader import filter_img_by_sample
        runner = filter_img_by_sample.SampleImgFilter()

    runner.run()

class CiftagParser:
    """cli args 파싱 및 해당 작업 호출"""
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            usage="""ciftag <command> [<args>]

        subcommands :
            celery      handling celery
            db          handling database
            api         execute api server
            crawl       execute crawler
            kafka       execute kafka consumer
        """,
        )
        self.parser.add_argument("command", help="Subcommand to run")

    def celery(self):
        """데이터베이스 관련 명령어 처리"""
        parser = argparse.ArgumentParser(
            prog="ciftag celery", description="handling celery"
        )
        subparsers = parser.add_subparsers()

        ht = "restart celery worker"
        parser = subparsers.add_parser("restart", help=ht)
        parser.add_argument(
            "worker",
            type=str,
            choices=['all', 'celery', 'task'],
            help="Specify the type of the crawler to run"
        )
        parser.set_defaults(func=restart_worker)

        return parser

    def db(self):
        """데이터베이스 관련 명령어 처리"""
        parser = argparse.ArgumentParser(
            prog="ciftag db", description="handling database"
        )
        subparsers = parser.add_subparsers()

        ht = "Initialize the database"
        parser_initdb = subparsers.add_parser("init", help=ht)
        # aws rds 초기 db 생성옵션
        parser_initdb.add_argument(
            "-a",
            "--aws",
            action="store_true",
            help="Set init aws db",
        )
        parser_initdb.set_defaults(func=initdb)

        return parser

    def api(self):
        """API 서버 실행 명령어 처리"""
        parser = argparse.ArgumentParser(
            prog="ciftag api", description="execute api server"
        )
        # api 실행과 함께 초기 db 생성
        parser.add_argument(
            "-i",
            "--initdb",
            action="store_true",
            help="Set init db",
        )
        # dev 모드 run 옵션
        parser.add_argument(
            "-d",
            "--develop",
            action="store_true",
            help="Develop Server",
        )
        parser.set_defaults(func=start_api_server)

        return parser

    def crawl(self):
        """수집기 실행 명령어 처리 (현재는 sqs 큐 소비 쪽만 구현)"""
        parser = argparse.ArgumentParser(
            prog="ciftag crawl", description="execute crawler (base on sqs only)"
        )
        parser.add_argument(
            "run_type",
            type=str,
            choices=['pinterest', 'tumblr', 'flicker', 'test'],
            help="Specify the type of the crawler to run"
        )
        parser.add_argument(
            "work_id",
            type=str,
            help="Specify the work ident"
        )
        parser.set_defaults(func=run_crawler)

        return parser

    def kafka(self):
        """수집기 실행 명령어 처리 (현재는 sqs 큐 소비 쪽만 구현)"""
        parser = argparse.ArgumentParser(
            prog="ciftag kafka", description="execute kafka consumer"
        )

        parser.add_argument(
            "operation",
            type=str,
            choices=['crawl', 'download'],
            help="Specify the operation type"
        )

        parser.add_argument(
            "consumer_type",
            type=str,
            help="Specify the type of the task for consumer"
        )

        parser.add_argument(
            "task_type",
            type=str,
            choices=['common', 'retry'],
            help="Specify the common or retry task"
        )

        # Validate arguments based on operation
        def validate_args(args):
            if args.operation == 'crawl' and args.consumer_type not in ['main', 'sub', 'agt']:
                parser.error("For 'crawl', consumer_type must be one of 'main', 'sub', 'agt'.")
            elif args.operation == 'download' and args.consumer_type not in ['img', 'filter']:
                parser.error("For 'download', consumer_type must be one of 'img', 'filter'.")
            return args
        
        def select_function(args):
            validate_args(args)
            if args.operation == 'crawl':
                run_crawl_consumer(args)
            elif args.operation == 'download':
                run_download_consumer(args)

        parser.set_defaults(func=select_function)

        return parser

    def parse_args(self):
        """bin parser"""
        args = self.parser.parse_args(sys.argv[1:2])

        if not hasattr(self, args.command):
            print("Unrecognized command")
            self.parser.print_help()
            self.parser.exit()

        subparser = getattr(self, args.command)()
        try:
            args = subparser.parse_args(sys.argv[2:])
        except TypeError as e:
            logs.log_data(f"TypeError on bin parser {e}")
            subparser.print_help()
            subparser.exit()

        try:
            args.func(args)
        except AttributeError as e:
            logs.log_data(f"AttributeError on bin parser {e}")
            subparser.print_help()
            subparser.exit()
