#!/bin/bash

echo "${SERVER_TYPE}"
echo "${RUN_TYPE}  수집기 실행"
echo "collector running" > start.done
ciftag crawl "${RUN_TYPE}"

# 최종 인자값 출력
echo "------ 최종 실행 인자 값: ${SERVER_TYPE} ${RUN_TYPE} ------"
