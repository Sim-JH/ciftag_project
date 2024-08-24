Local Crawl Workflow
1. API 호출 [web]
2. celery 작업 생성 및 트리거 / 외부 작업 (work_info log insert) [orchestrator]
3. 크롤러 호출 / 내부 작업 (task_info log insert) [tasks]
4. 크롤링 작업 실행 / 내부 작업 (task_info log update) [services]
   모든 worker 작업 종료 대기 후 후처리 트리거 (2번 작업에서 celery로 예약)
5. 후처리 및 airflow 호출 / 외부 작업 (work_info log update) [tasks]

AWS Crawl Workflow
1. API 호출 [web]
2. sqs push 및 github action 트리거 / 외부 작업 (work_info log insert) [orchestrator]
3. 크롤러 호출 / 내부 작업 (task_info log insert) [fargate]
4. 크롤링 작업 실행 / 내부 작업 (task_info log update) [services]
   모든 ecs container 작업 종료 대기 후 후처리 트리거 (task_info log 기반으로 컨테이너 작업 상황 파악)
5. 후처리 및 airflow 호출 / 외부 작업 (work_info log update) [fargate]