# 3조 결과 페이지를 nginx 로 띄운다
#   빌드: docker build -t team3-report -f jisu/final/web/Dockerfile jisu/final
#   실행: docker run -d --name team3-report -p 127.0.0.1:8080:80 team3-report
#   열기: http://localhost:8080 (스토리 페이지) · http://localhost:8080/dashboard.html (모니터링: 대시보드 · 입력 기록 · 유형별 검출 · 주의 조건 · 경보 기준)
FROM nginx:1.27-alpine
COPY 스토리페이지.html /usr/share/nginx/html/index.html
COPY monitor/*.html monitor/*.css monitor/*.js /usr/share/nginx/html/
