# jisu — 모델 실험 · 최종 모델

최종 모델은 **KNN** (MinMax · k=15 · 맨해튼 거리 · 거리 가중), public macro F1 **0.5890** (3회차).

| 무엇 | 위치 |
|---|---|
| 최종 코드 | `../결과/main.py` (= `main.py`) — `학생배포/` 안에서 `python main.py` → `제출_3조.csv` |
| 최종 제출 파일 | `../결과/제출_3조_최종.csv` — `main.py` 를 다시 돌린 결과와 2,261샷 모두 같음 |
| 최종 보고서 | `final/보고서_3조.pdf` · `final/보고서_3조.docx` (원본 `final/보고서_최종.html`) |
| 실험 정리 | `실험정리.md` — 리더보드 7회 · 데이터 발견 · 평가 방법 · 실험 결과 전부 |
| KNN 설정 과정 | `KNN_파라미터_정리.txt` — 84개 조합 비교 · 최종 파라미터 · 점수 |
| 데이터 문제와 처리 | `final/보고서_1_데이터문제와처리.md` |

## 폴더

| 경로 | 내용 |
|---|---|
| `main.py` | 최종 KNN 제출 코드 |
| `main_ensemble.py` | KNN 0.4 + RF 0.4 + 제품별 XGB 0.2 앙상블 (6회차, 비교용) |
| `main_knn_rf.py` · `main_knn_process.py` · `main_pseudo.py` | 비교용 제출 코드 (KNN+RF · 파생 변수 4개 · 수도 라벨링) |
| `plr_mlp_process.py` | PLR MLP + 파생 변수 4개 (7회차) |
| `models/` | 실험 스크립트 `cv_*.py` — 같은 fold 짝 비교로 KNN 과 비교 (`_common.py` 가 공통 데이터 · fold) |
| `final/` | 보고서용 코드 (`report_numbers.py` 보고서 숫자 · `mlp.py` MLP 실험과 학습곡선 · `data_pre.py` 전처리) · 그림 `figures/` |
| `model2/` | 앙상블 비교 코드, `제출_3조.csv` = 6회차 앙상블 예측 (최종 KNN 과 43샷 다름) |

## 최종이 아닌 제출 파일

- `제출_4조.csv` — 10/27 실험 결과로 덮어쓴 파일. 최종 KNN 과 62샷 다름. **제출에 쓰지 않음**
- `제출_XGB_KNN.csv` — 실험 제출 파일
- `model2/제출_3조.csv` — 6회차 앙상블 예측
