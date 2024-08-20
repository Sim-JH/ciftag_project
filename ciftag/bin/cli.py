import sys
import time
import argparse

import uvicorn
import sqlalchemy

import ciftag.utils.logger as logger
from ciftag.utils import bootstrap
from ciftag.web.app import create_app
from ciftag.configuration import conf


logs = logger.Logger(log_dir='CLI')


def initdb(args):
    """데이터베이스 초기화"""
    bootstrap.initdb()


def start_api_server(args):
    """API 서버 시작. 필요 시 데이터베이스 초기화도 수행"""
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


class CiftagParser:
    """cli args 파싱 및 해당 작업 호출"""
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            usage="""ciftag <command> [<args>]

        subcommands :
            db          handling database
            api         execute api server
        """,
        )
        self.parser.add_argument("command", help="Subcommand to run")

    def db(self):
        """데이터베이스 관련 명령어 처리"""
        parser = argparse.ArgumentParser(
            prog="ciftag db", description="handling database"
        )
        subparsers = parser.add_subparsers()

        ht = "Initialize the database"
        parser_initdb = subparsers.add_parser("init", help=ht)
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
