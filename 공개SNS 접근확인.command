#!/bin/bash
mkdir -p "$HOME/Projects/fimi/logs"; exec > >(tee "$HOME/Projects/fimi/logs/공개SNS 접근확인.log") 2>&1
# 맥에서 공개 SNS 소스가 열리는지 1분 안에 확인 (작업 세션 환경에서는 403이라 맥에서 봐야 한다)
echo "1) Bluesky 공개 검색 API"; curl -s -o /dev/null -w "   HTTP %{http_code}\n" --max-time 15 "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=%ED%95%9C%EB%AF%B8%EB%8F%99%EB%A7%B9&limit=5"
echo "2) Bluesky Jetstream(실시간 스트림, 인증 없음)"; curl -s -o /dev/null -w "   HTTP %{http_code} (101/400이면 서버는 열림)\n" --max-time 10 "https://jetstream2.us-east.bsky.network/xrpc/_health"
echo "3) Mastodon 공개 타임라인(mastodon.social)"; curl -s -o /dev/null -w "   HTTP %{http_code}\n" --max-time 15 "https://mastodon.social/api/v1/timelines/public?limit=5"
echo "4) GDELT 15분 원본 목록"; curl -s -o /dev/null -w "   HTTP %{http_code}\n" --max-time 15 "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
echo; echo "200이면 열린 것. 1)이 403이면 live/collect.py 의 bluesky 소스는 끄고 Mastodon·GDELT로 간다."; echo "[끝] $(date)"; sleep 3
