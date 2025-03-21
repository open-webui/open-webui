PORT="${PORT:-8080}"

# --reset 옵션이 있으면 logs 폴더의 모든 로그 삭제
# 로그가 너무 많이 쌓이면 용량이 커지고, 로그 파일을 열 때 시간이 오래 걸릴 수 있음
if [[ "$1" == "--reset" ]]; then
    echo -e "\033[1;33m==============================\033[0m"
    echo -e "\033[1;31m🚨 Resetting log files... 🚨\033[0m"
    echo -e "\033[1;33m==============================\033[0m"
    rm -rf logs/*
fi

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload