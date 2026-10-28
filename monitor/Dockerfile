# 3조 결과 페이지를 nginx 로 띄운다 (저장소 루트에서 실행)
#   빌드: docker build -t team3-report monitor
#   실행: docker run -d --name team3-report -p 127.0.0.1:8080:80 team3-report
#   열기: http://localhost:8080 (스토리 페이지) · http://localhost:8080/dashboard.html (모니터링)
FROM nginx:1.27-alpine
COPY 스토리페이지.html /usr/share/nginx/html/index.html
COPY dashboard.html feed.html types.html conditions.html rules.html report.html monitor.css monitor.js feed_data.js /usr/share/nginx/html/
