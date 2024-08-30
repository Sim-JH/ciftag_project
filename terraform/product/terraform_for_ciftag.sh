#!/bin/bash

i=0
echo "${SERVER_TYPE}"
echo "${RUN_TYPE}"

if [ ${SERVER_TYPE} = "dev" ]
    then
        for ((i=0; i<=${ECS_COUNT_CIFTAG}; i++))
        do
            echo "ciftag ${SERVER_TYPE} ${i} 실행"
            terraform apply -auto-approve -input=false -var="desired_count_tasks_fargate_ciftag=1" -var="init_count_fargate_ciftag=1" -var="server_type=${SERVER_TYPE}" -var="run_type=${RUN_TYPE}" -var="crypto_key=${CRYPTO_KEY}"
            sleep 3
        done
fi

if [ ${SERVER_TYPE} = "product" ]
    then
        for ((i=0; i<=${ECS_COUNT_CIFTAG}; i++))
        do
            echo "ciftag ${SERVER_TYPE} ${i} 실행"
            terraform apply -auto-approve -input=false -var="desired_count_tasks_fargate_ciftag=${ECS_COUNT_CIFTAG}" -var="init_count_fargate_ciftag=3" -var="server_type=${SERVER_TYPE}" -var="run_type=${RUN_TYPE}" -var="crypto_key=${CRYPTO_KEY}"
            sleep 3
        done
fi

echo "테라폼 실행 완료"

# 남은 큐 확인
aws sqs get-queue-attributes --queue-url https://sqs.ap-northeast-2.amazonaws.com/617204753570/ciftag-dev --attribute-names ApproximateNumberOfMessages
