# 모니터링 페이지용 입력 데이터: public/private 샷을 shot_id 순으로, 최종 제출 예측을 붙여 feed_data.js 로 쓴다
# 실행: python3 jisu/final/monitor/make_feed.py
import csv, json, sys
from pathlib import Path
root = str(Path(__file__).resolve().parents[3]) + "/"  # 저장소 루트
rows = list(csv.DictReader(open(root + "jisu/final/전처리_결과.csv", encoding="utf-8-sig")))
pred = {r["shot_id"]: r["label"] for r in csv.DictReader(open(root + "jisu/model2/제출_3조.csv", encoding="utf-8-sig"))}
LAB = {"정상": 0, "불량_Short_Shot": 1, "불량_Blow_Hole": 2, "불량_Exfoliation": 3, "불량_Stain": 4, "불량_Deformation": 5, "기타불량": 6}

# 얼룩 조건: 제품 2 train 냉각수 압력 상위 1/3 경계
p2 = sorted(float(r["Coolant_Pressure"]) for r in rows if r["split"] == "train" and r["Product_Type"] == "2")
q = 2.74  # ≥ 2.74 이면 762샷 · 얼룩 9.7% (보고서 수치와 일치 확인)
print("product2 train n", len(p2), "coolant pressure upper-third cut", q, file=sys.stderr)

F = ["Product_Type", "Melting_Furnace_Temp", "Coolant_Temp", "Coolant_Pressure", "Casting_Pressure", "Cycle_Time", "Factory_Temp", "Spray_Time", "Spray_1_Time"]
out, miss = [], 0
for r in sorted((r for r in rows if r["split"] in ("public", "private")), key=lambda r: int(r["shot_id"])):
    if r["shot_id"] not in pred: miss += 1; continue
    out.append([int(r["shot_id"])] + [float(r[f]) for f in F] + [LAB[pred[r["shot_id"]]]])
print("shots", len(out), "missing pred", miss, file=sys.stderr)
with open(root + "jisu/final/monitor/feed_data.js", "w", encoding="utf-8") as f:
    f.write("// 자동 생성: jisu/final/monitor/make_feed.py · test(public+private) 샷 shot_id 순 · 예측 = jisu/model2/제출_3조.csv\n")
    f.write("// [shot_id, 제품, 용탕로 온도, 냉각수 온도, 냉각수 압력, 주조 압력, 사이클, 공장 온도, 분사 시간, Spray_1_Time, 예측 코드]\n")
    f.write(f"window.STAIN_CUT = {q};\nwindow.FEED = {json.dumps(out, separators=(',', ':'))};\n")
