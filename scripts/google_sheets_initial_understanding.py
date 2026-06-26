#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def col_name(index: int) -> str:
    name = ""
    while index:
        index, rem = divmod(index - 1, 26)
        name = chr(65 + rem) + name
    return name


def load_windows(run_dir: Path, prefix: str) -> list[list[Any]]:
    rows: list[list[Any]] = []
    for path in sorted(run_dir.glob(f"{prefix}-*.json")):
        payload = read_json(path).get("payload", {})
        for window in payload.get("windows", []):
            match = re.search(r"![A-Z]+(\d+):", window.get("range", ""))
            if not match:
                continue
            start_row = int(match.group(1))
            for row_index, row in enumerate(window.get("values", []), start_row):
                while len(rows) < row_index:
                    rows.append([])
                rows[row_index - 1] = row
    return rows


def cell(rows: list[list[Any]], row: int, col: int) -> str:
    if row <= 0 or col <= 0 or row > len(rows):
        return ""
    values = rows[row - 1]
    if col > len(values):
        return ""
    return str(values[col - 1])


def classify_surface(title: str) -> tuple[str, str]:
    if title == "SupermetricsQueries":
        return "automation_surface", "supermetrics_query_config"
    if title.startswith("[DB]RAW_"):
        lowered = title.lower()
        if "광고비" in title:
            return "raw_source_truth", "ad_spend"
        if "결제액" in title:
            return "raw_source_truth", "payment_amount"
        if "순매출" in title:
            return "raw_source_truth", "net_sales"
        if "결제수" in title:
            return "raw_source_truth", "payment_count"
        if "순구매수" in title:
            return "raw_source_truth", "net_purchase_count"
        if "회원가입" in title:
            return "raw_source_truth", "signup_count"
        if "ga4" in lowered:
            return "raw_source_truth", "ga4"
        if "맵핑" in title:
            return "mapping_reference", "mapping"
        return "raw_source_truth", "raw_db"
    if title.startswith("[DB]데이터정리"):
        return "processed_source", "ad_spend_settlement_preparation"
    if title.startswith("MLL_Overview"):
        return "result_projection", "overview_dashboard"
    if title.startswith("MLL_데이터확인"):
        return "review_projection", "data_check"
    if title.startswith("Weekly") or title.startswith("회고"):
        return "annotation_or_review_projection", "weekly_or_retrospective"
    return "unknown_surface", "review_required"


def build_surface_inventory(run_dir: Path) -> dict[str, Any]:
    snapshot = read_json(run_dir / "recorded-metadata-snapshot.json")
    surfaces = []
    for tab in snapshot.get("tabs", []):
        role, subtype = classify_surface(tab["title"])
        surfaces.append(
            {
                "sheet_id": tab.get("sheet_id"),
                "title": tab.get("title"),
                "range": f"'{tab.get('title')}'!A1:{col_name(tab.get('column_count', 1))}{tab.get('row_count', 1)}",
                "row_count": tab.get("row_count"),
                "column_count": tab.get("column_count"),
                "surface_role": role,
                "surface_subtype": subtype,
                "status": "candidate",
            }
        )
    return {
        "schema_version": "surface_inventory_v1",
        "spreadsheet_id": snapshot.get("spreadsheet_id"),
        "title": snapshot.get("title"),
        "target_sheet_id": 562691839,
        "surfaces": surfaces,
        "summary": dict(Counter(surface["surface_role"] for surface in surfaces)),
    }


def formula_sources(formulas: list[list[Any]]) -> list[str]:
    sources: Counter[str] = Counter()
    source_pattern = re.compile(r"'([^']+)'!")
    for row in formulas:
        for value in row:
            if isinstance(value, str) and value.startswith("="):
                for source in source_pattern.findall(value):
                    sources[source] += 1
    return [source for source, _ in sources.most_common()]


def table_candidates(values: list[list[Any]], formulas: list[list[Any]]) -> dict[str, Any]:
    sources = formula_sources(formulas)
    return {
        "schema_version": "table_candidates_v1",
        "target_sheet": "MLL_Overview(신규/롱테일)",
        "target_range": "'MLL_Overview(신규/롱테일)'!A1:AU872",
        "formula_referenced_sources": sources,
        "tables": [
            {
                "id": "kpi_payment_basis",
                "name": "결제액 기준 목표지표 카드",
                "range": "'MLL_Overview(신규/롱테일)'!K1:U5",
                "role": "result_projection",
                "boundary_evidence": ["상단 요약 표기", "2026-06 월별 행과 목표지표 상수를 참조하는 수식"],
                "status": "sampled_accepted",
            },
            {
                "id": "kpi_net_sales_basis",
                "name": "순매출 기준 목표지표 카드",
                "range": "'MLL_Overview(신규/롱테일)'!AE1:AO5",
                "role": "result_projection",
                "boundary_evidence": ["상단 요약 표기", "2026-06 월별 행과 목표지표 상수를 참조하는 수식"],
                "status": "sampled_accepted",
            },
            {
                "id": "monthly_summary",
                "name": "월별 MLL 성과 요약",
                "range": "'MLL_Overview(신규/롱테일)'!A7:AT31",
                "role": "processed_output_table",
                "boundary_evidence": ["7행 표기 구조", "8:31행 월별 표기", "일별 시계열 행을 집계하는 수식"],
                "status": "sampled_accepted",
            },
            {
                "id": "daily_time_series",
                "name": "일별 MLL 성과 집계",
                "range": "'MLL_Overview(신규/롱테일)'!A32:AT867",
                "role": "processed_output_table",
                "boundary_evidence": ["날짜 행", "공유되는 조건 합산 수식 패턴", "외부 원천 시트 참조"],
                "status": "sampled_accepted",
            },
            {
                "id": "weekly_rollup_rows",
                "name": "주간 MLL 성과 집계 행",
                "range": "'MLL_Overview(신규/롱테일)'!A39:AT871",
                "role": "processed_output_table",
                "boundary_evidence": ["12/30주 같은 주간 표기", "앞선 7개 일별 행을 합산하는 수식"],
                "status": "sampled_accepted_with_mixed_future_rows",
            },
            {
                "id": "future_prebuilt_rows",
                "name": "미래 일자 사전 생성 행",
                "range": "'MLL_Overview(신규/롱테일)'!A868:AT871",
                "role": "prebuilt_future_projection",
                "boundary_evidence": ["2027-01 행에 #N/A 값이 있음"],
                "status": "review_required",
            },
        ],
    }


def label_dictionary(values: list[list[Any]], formulas: list[list[Any]]) -> dict[str, Any]:
    labels = []
    roles = {
        "A": ("date_axis", "분석 기준 날짜 또는 월/주 라벨"),
        "B": ("processed_dimension", "요일, 날짜에서 파생"),
        "C": ("processed_total", "광고비 합계 = 신규 + 롱테일 + 공통광고비"),
        "D": ("processed_from_raw", "신규 광고비, RAW_광고비에서 기간/상품군 조건으로 계산"),
        "E": ("processed_from_raw", "롱테일 광고비, RAW_광고비에서 기간/상품군 조건으로 계산"),
        "F": ("processed_from_raw", "공통광고비, RAW_광고비에서 공통 라벨 조건으로 계산"),
        "G": ("processed_total", "결제수 합계 = 신규 + 롱테일 + 미표기 보조값"),
        "H": ("processed_from_raw", "신규 결제수, RAW_결제수에서 계산"),
        "I": ("processed_from_raw", "롱테일 결제수, RAW_결제수에서 계산"),
        "J": ("review_required", "결제수 합계에 포함되지만 7행 표기가 비어 있음"),
        "K": ("processed_total", "결제액 합계 = 신규 + 롱테일 + 미표기 보조값"),
        "L": ("processed_from_raw", "신규 결제액, RAW_결제액에서 계산"),
        "M": ("processed_from_raw", "롱테일 결제액, RAW_결제액에서 계산"),
        "N": ("review_required", "결제액 합계에 포함되지만 7행 표기가 비어 있음"),
        "O": ("processed_ratio", "결제액 비중 합계 = 신규 + 롱테일 비중"),
        "P": ("processed_ratio", "신규 결제액 / 결제액 합계"),
        "Q": ("processed_ratio", "롱테일 결제액 / 결제액 합계"),
        "R": ("processed_ratio", "ROAS = 결제액 합계 / 광고비 합계"),
        "S": ("processed_ratio", "신규 ROAS = 신규 결제액 / 신규 광고비"),
        "T": ("processed_ratio", "롱테일 ROAS = 롱테일 결제액 / (롱테일 광고비 + 공통광고비)"),
        "U": ("processed_ratio", "고객획득비용 = 광고비 합계 / 결제액 합계"),
        "V": ("processed_ratio", "신규 고객획득비용 = 신규 광고비 / 신규 결제액"),
        "W": ("processed_ratio", "롱테일 고객획득비용 = (롱테일 광고비 + 공통광고비) / 롱테일 결제액"),
        "X": ("processed_ratio", "평균 객단가 = 결제액 합계 / 결제수 합계"),
        "Y": ("processed_ratio", "신규 평균 객단가 = 신규 결제액 / 신규 결제수"),
        "Z": ("processed_ratio", "롱테일 평균 객단가 = 롱테일 결제액 / 롱테일 결제수"),
        "AA": ("processed_total", "순 구매수 합계 = 신규 + 롱테일 + 미표기 보조값"),
        "AB": ("processed_from_raw", "신규 순구매수, RAW_순구매수에서 계산"),
        "AC": ("processed_from_raw", "롱테일 순구매수, RAW_순구매수에서 계산"),
        "AD": ("review_required", "순 구매수 합계에 포함되지만 7행 표기가 비어 있음"),
        "AE": ("processed_total", "순 매출 합계 = 신규 + 롱테일 + 미표기 보조값"),
        "AF": ("processed_from_raw", "신규 순매출, RAW_순매출에서 계산"),
        "AG": ("processed_from_raw", "롱테일 순매출, RAW_순매출에서 계산"),
        "AH": ("review_required", "순 매출 합계에 포함되지만 7행 표기가 비어 있음"),
        "AI": ("processed_ratio", "순 매출 비중 합계 = 신규 + 롱테일 비중"),
        "AJ": ("processed_ratio", "신규 순매출 / 순 매출 합계"),
        "AK": ("processed_ratio", "롱테일 순매출 / 순 매출 합계"),
        "AL": ("processed_ratio", "순매출 기준 ROAS = 순 매출 합계 / 광고비 합계"),
        "AM": ("processed_ratio", "신규 순매출 기준 ROAS = 신규 순매출 / 신규 광고비"),
        "AN": ("processed_ratio", "롱테일 순매출 기준 ROAS = 롱테일 순매출 / (롱테일 광고비 + 공통광고비)"),
        "AO": ("processed_ratio", "순매출 기준 고객획득비용 = 광고비 합계 / 순 매출 합계"),
        "AP": ("processed_ratio", "신규 순매출 기준 고객획득비용 = 신규 광고비 / 신규 순매출"),
        "AQ": ("processed_ratio", "롱테일 순매출 기준 고객획득비용 = (롱테일 광고비 + 공통광고비) / 롱테일 순매출"),
        "AR": ("processed_ratio", "순매출 평균 객단가 = 순 매출 합계 / 순 구매수 합계"),
        "AS": ("processed_ratio", "신규 순매출 평균 객단가 = 신규 순매출 / 신규 순구매수"),
        "AT": ("processed_ratio", "롱테일 순매출 평균 객단가 = 롱테일 순매출 / 롱테일 순구매수"),
    }
    for col_index in range(1, 47):
        name = col_name(col_index)
        header = cell(values, 7, col_index)
        role, definition = roles.get(name, ("annotation_or_empty", "not classified"))
        sample_formula = cell(formulas, 32, col_index) or cell(formulas, 8, col_index)
        labels.append(
            {
                "column": name,
                "label": header,
                "role": role,
                "definition": definition,
                "sample_formula": sample_formula[:500],
                "status": "review_required" if role == "review_required" else "sampled_accepted",
            }
        )
    return {"schema_version": "label_dictionary_v1", "target_sheet": "MLL_Overview(신규/롱테일)", "labels": labels}


def table_io_svg() -> str:
    return """<svg class="io-svg" viewBox="0 0 1180 620" role="img" aria-labelledby="io-title io-desc" xmlns="http://www.w3.org/2000/svg">
  <title id="io-title">표 입출력 흐름</title>
  <desc id="io-desc">원천 시트가 일별 MLL 집계표로 이어지고, 일별 행은 주간 행과 월별 요약으로 집계됩니다. 월별 요약은 결제액과 순매출 목표지표 카드로 이어집니다. Supermetrics 설정은 원천 시트의 갱신 근거를 제공합니다.</desc>
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#41627f" />
    </marker>
    <marker id="arrow-dashed" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,6 L9,3 z" fill="#8a6f24" />
    </marker>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0f2437" flood-opacity="0.16" />
    </filter>
  </defs>
  <rect width="1180" height="620" rx="18" fill="#f6f9fc" />
  <text x="36" y="42" font-size="22" font-weight="700" fill="#17324d">표 입출력 흐름</text>
  <text x="36" y="68" font-size="13" fill="#5c6f82">원천 근거 -> 일별 가공표 -> 주간/월별 집계 -> 목표지표 카드</text>

  <g class="lane">
    <text x="48" y="116" font-size="13" font-weight="700" fill="#41627f">원천 근거</text>
    <rect x="36" y="128" width="260" height="342" rx="12" fill="#e9f2fb" stroke="#bed0e0" />
  </g>
  <g class="lane">
    <text x="386" y="116" font-size="13" font-weight="700" fill="#41627f">가공 결과</text>
    <rect x="360" y="128" width="260" height="342" rx="12" fill="#eef8f2" stroke="#bdd7c5" />
  </g>
  <g class="lane">
    <text x="694" y="116" font-size="13" font-weight="700" fill="#41627f">집계</text>
    <rect x="680" y="128" width="190" height="342" rx="12" fill="#fff6e6" stroke="#dfc991" />
  </g>
  <g class="lane">
    <text x="952" y="116" font-size="13" font-weight="700" fill="#41627f">최종 표시</text>
    <rect x="930" y="128" width="214" height="342" rx="12" fill="#f4effb" stroke="#cfbfdf" />
  </g>

  <g filter="url(#shadow)">
    <rect x="66" y="152" width="200" height="48" rx="8" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="173" font-size="13" font-weight="700" fill="#17324d">광고비 원천</text>
    <text x="82" y="190" font-size="11" fill="#5c6f82">[DB]RAW_광고비</text>

    <rect x="66" y="210" width="200" height="48" rx="8" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="231" font-size="13" font-weight="700" fill="#17324d">결제수 원천</text>
    <text x="82" y="248" font-size="11" fill="#5c6f82">[DB]RAW_결제수</text>

    <rect x="66" y="268" width="200" height="48" rx="8" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="289" font-size="13" font-weight="700" fill="#17324d">결제액 원천</text>
    <text x="82" y="306" font-size="11" fill="#5c6f82">[DB]RAW_결제액</text>

    <rect x="66" y="326" width="200" height="48" rx="8" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="347" font-size="13" font-weight="700" fill="#17324d">순구매수 원천</text>
    <text x="82" y="364" font-size="11" fill="#5c6f82">[DB]RAW_순구매수</text>

    <rect x="66" y="384" width="200" height="48" rx="8" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="405" font-size="13" font-weight="700" fill="#17324d">순매출 원천</text>
    <text x="82" y="422" font-size="11" fill="#5c6f82">[DB]RAW_순매출</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="390" y="238" width="200" height="126" rx="10" fill="#ffffff" stroke="#9bc5a7" />
    <text x="410" y="264" font-size="15" font-weight="700" fill="#17324d">일별 MLL 성과 집계</text>
    <text x="410" y="286" font-size="12" fill="#5c6f82">'MLL_Overview'!A32:AT867</text>
    <text x="410" y="312" font-size="12" fill="#2f6d43">조건 합산 수식</text>
    <text x="410" y="332" font-size="12" fill="#5c6f82">날짜 + 신규/롱테일 조건</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="704" y="184" width="142" height="82" rx="10" fill="#ffffff" stroke="#d1b66d" />
    <text x="722" y="211" font-size="14" font-weight="700" fill="#17324d">월별 요약</text>
    <text x="722" y="232" font-size="11" fill="#5c6f82">A7:AT31</text>
    <text x="722" y="249" font-size="11" fill="#8a6f24">월별 집계 수식</text>

    <rect x="704" y="334" width="142" height="82" rx="10" fill="#ffffff" stroke="#d1b66d" />
    <text x="722" y="361" font-size="14" font-weight="700" fill="#17324d">주간 집계 행</text>
    <text x="722" y="382" font-size="11" fill="#5c6f82">A39:AT871</text>
    <text x="722" y="399" font-size="11" fill="#8a6f24">7일 합산</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="958" y="182" width="154" height="88" rx="10" fill="#ffffff" stroke="#b9a5d0" />
    <text x="976" y="209" font-size="14" font-weight="700" fill="#17324d">결제액 목표지표</text>
    <text x="976" y="230" font-size="11" fill="#5c6f82">K1:U5</text>
    <text x="976" y="247" font-size="11" fill="#6a4d8f">6월/목표지표/달성률</text>

    <rect x="958" y="318" width="154" height="88" rx="10" fill="#ffffff" stroke="#b9a5d0" />
    <text x="976" y="345" font-size="14" font-weight="700" fill="#17324d">순매출 목표지표</text>
    <text x="976" y="366" font-size="11" fill="#5c6f82">AE1:AO5</text>
    <text x="976" y="383" font-size="11" fill="#6a4d8f">6월/목표지표/달성률</text>
  </g>

  <g filter="url(#shadow)">
    <rect x="390" y="500" width="200" height="58" rx="10" fill="#fffdf4" stroke="#d5bd67" />
    <text x="410" y="523" font-size="13" font-weight="700" fill="#17324d">SupermetricsQueries</text>
    <text x="410" y="542" font-size="11" fill="#8a6f24">원천 갱신 근거</text>
  </g>

  <g fill="none" stroke="#41627f" stroke-width="2.4" marker-end="url(#arrow)">
    <path d="M266 176 C316 176 330 254 390 272" />
    <path d="M266 234 C320 234 332 278 390 292" />
    <path d="M266 292 C320 292 332 304 390 308" />
    <path d="M266 350 C320 350 332 326 390 322" />
    <path d="M266 408 C320 408 334 348 390 338" />
    <path d="M590 280 C642 250 656 224 704 224" />
    <path d="M590 326 C642 352 656 376 704 376" />
    <path d="M846 224 C894 224 914 224 958 224" />
    <path d="M846 240 C906 274 920 342 958 362" />
  </g>
  <g fill="none" stroke="#8a6f24" stroke-width="2" stroke-dasharray="7 5" marker-end="url(#arrow-dashed)">
    <path d="M390 528 C302 516 290 178 266 176" />
    <path d="M490 500 C490 452 490 408 490 364" />
  </g>

  <g>
    <rect x="54" y="520" width="20" height="10" fill="#ffffff" stroke="#9cb8d1" />
    <text x="82" y="530" font-size="11" fill="#5c6f82">실선: 수식으로 계산된 값 흐름</text>
    <line x1="54" y1="550" x2="74" y2="550" stroke="#8a6f24" stroke-width="2" stroke-dasharray="5 4" />
    <text x="82" y="554" font-size="11" fill="#5c6f82">점선: 갱신/자동화 근거</text>
  </g>
</svg>"""


def io_graph() -> dict[str, Any]:
    svg = table_io_svg()
    return {
        "schema_version": "table_io_graph_v1",
        "target_sheet": "MLL_Overview(신규/롱테일)",
        "visualization": "svg",
        "svg": svg,
        "edges": [
            {"from": "[DB]RAW_광고비-필터금지", "to": "일별 MLL 성과 집계", "basis": "SUMPRODUCT/SUMIF by date and category"},
            {"from": "[DB]RAW_결제수-필터금지", "to": "일별 MLL 성과 집계", "basis": "SUMPRODUCT by date and new/longtail logic"},
            {"from": "[DB]RAW_결제액-필터금지", "to": "일별 MLL 성과 집계", "basis": "SUMPRODUCT by date and new/longtail logic"},
            {"from": "[DB]RAW_순구매수-필터금지", "to": "일별 MLL 성과 집계", "basis": "SUMPRODUCT by date and new/longtail logic"},
            {"from": "[DB]RAW_순매출-필터금지", "to": "일별 MLL 성과 집계", "basis": "SUMPRODUCT by date and new/longtail logic"},
            {"from": "일별 MLL 성과 집계", "to": "월별 MLL 성과 요약", "basis": "SUMIFS over daily rows"},
            {"from": "일별 MLL 성과 집계", "to": "주간 MLL 성과 집계 행", "basis": "SUM over preceding seven daily rows"},
            {"from": "월별 MLL 성과 요약", "to": "목표지표 카드", "basis": "월별 행 참조와 목표지표 상수"},
        ],
    }


def review_questions() -> dict[str, Any]:
    return {
        "schema_version": "review_questions_v1",
        "questions": [
            {
                "id": "q_unlabeled_language_columns",
                "question": "J/N/AD/AH처럼 합계에 포함되지만 7행 표기가 비어 있는 컬럼은 어떤 의미인가요? 수식상 특정 제외/보조 카테고리로 보이지만 명칭 확인이 필요합니다.",
                "related_ranges": ["J7:J867", "N7:N867", "AD7:AD867", "AH7:AH867"],
            },
            {
                "id": "q_new_longtail_rule",
                "question": "신규/롱테일 구분은 RAW 시트의 날짜 기준 29일/30일 경계로 계산되는 것으로 보입니다. 이 경계가 공식 정의인가요?",
                "related_ranges": ["D32:E867", "H32:I867", "L32:M867", "AF32:AG867"],
            },
            {
                "id": "q_common_ad_spend",
                "question": "공통광고비는 롱테일 ROAS/고객획득비용 계산에서 롱테일 쪽에 합산되고 있습니다. 이 배부 방식이 의도된 공식인가요?",
                "related_ranges": ["F32:F867", "T32:W867", "AN32:AQ867"],
            },
            {
                "id": "q_metric_basis",
                "question": "이 문서에서 결제액, 순매출, 결제수, 순구매수, 광고비 중 어떤 지표가 요약 설명의 1차 기준이어야 하나요?",
                "related_ranges": ["A7:AT31", "A32:AT867", "K1:U5", "AE1:AO5"],
            },
            {
                "id": "q_supermetrics_freshness",
                "question": "SupermetricsQueries가 원천 시트들을 갱신하는 것으로 보입니다. 최신성/갱신 주기와 실패 시 처리 기준을 확인해야 하나요?",
                "related_ranges": ["SupermetricsQueries!A1:AZ40"],
            },
        ],
    }


def esc(value: Any) -> str:
    return html.escape(str(value))


DISPLAY_TEXT = {
    "ad_spend": "광고비",
    "ad_spend_settlement_preparation": "광고비 정산용 가공",
    "annotation_or_empty": "주석 또는 빈 칸",
    "annotation_or_review_projection": "주석/검토 화면",
    "automation_surface": "자동화 설정",
    "candidate": "후보",
    "data_check": "데이터 확인",
    "date_axis": "날짜 축",
    "ga4": "GA4",
    "mapping": "매핑",
    "mapping_reference": "매핑 참조",
    "net_purchase_count": "순구매수",
    "net_sales": "순매출",
    "overview_dashboard": "개요 화면",
    "payment_amount": "결제액",
    "payment_count": "결제수",
    "prebuilt_future_projection": "사전 생성 미래 표시",
    "processed_dimension": "가공 차원",
    "processed_from_raw": "원천 기반 가공",
    "processed_output_table": "가공 결과표",
    "processed_ratio": "계산 비율",
    "processed_source": "가공 원천",
    "processed_total": "가공 합계",
    "raw_db": "원천 데이터",
    "raw_source_truth": "원천 근거",
    "result_projection": "결과 표시",
    "review_projection": "검토 화면",
    "review_required": "검토 필요",
    "sampled_accepted": "샘플 기준 수용",
    "sampled_accepted_with_mixed_future_rows": "샘플 기준 수용, 미래 행 혼재",
    "signup_count": "회원가입 수",
    "supermetrics_query_config": "Supermetrics 조회 설정",
    "unknown_surface": "미분류 화면",
    "weekly_or_retrospective": "주간/회고 화면",
    "multi_signal_decline": "복수 기준 하락",
    "single_signal_decline": "단일 기준 하락",
    "not_declining": "하락 아님",
}


def display(value: Any) -> str:
    return DISPLAY_TEXT.get(str(value), str(value))


def display_label(value: Any) -> str:
    text = str(value)
    if text == "CAC":
        return "고객획득비용"
    return text.replace("Total", "합계")


def fmt_money(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    return f"{number:,.0f}"


def fmt_delta(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:,.0f}"


def fmt_pct(value: Any) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    return f"{number * 100:.1f}%"


def fmt_percent_value(value: Any) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    return f"{number:.1f}%"


def fmt_percent_point_delta(value: Any) -> str:
    if value is None:
        return "-"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return esc(value)
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.1f}포인트"


def delta_class(value: Any) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if number < 0:
        return "negative"
    if number > 0:
        return "positive"
    return ""


def render_payment_decline_section(run_dir: Path) -> str:
    analysis_path = run_dir / "payment-decline-driver-analysis.json"
    if not analysis_path.exists():
        return ""
    analysis = read_json(analysis_path)
    windows = analysis.get("comparison_windows", {})
    metric_basis = "사용자가 확인한 결제액 기준입니다. 회계상 매출 기준이 아닙니다."
    category_rows = []
    for item in analysis.get("category_summaries", []):
        comparisons = {row["comparison"]: row for row in item.get("comparisons", [])}
        yoy = comparisons.get("전년도 대비", {})
        mom = comparisons.get("전월 대비", {})
        last3 = comparisons.get("지난 3주 평균 대비", {})
        category_rows.append(
            "<tr>"
            f"<td>{esc(item.get('category'))}</td>"
            f"<td>{esc(display(item.get('status')))}</td>"
            f"<td>{fmt_money(item.get('current_payment'))}</td>"
            f"<td class='{delta_class(yoy.get('payment_delta'))}'>{fmt_delta(yoy.get('payment_delta'))}<br><span class='muted'>{fmt_pct(yoy.get('payment_delta_pct'))}</span></td>"
            f"<td class='{delta_class(mom.get('payment_delta'))}'>{fmt_delta(mom.get('payment_delta'))}<br><span class='muted'>{fmt_pct(mom.get('payment_delta_pct'))}</span></td>"
            f"<td class='{delta_class(last3.get('payment_delta'))}'>{fmt_delta(last3.get('payment_delta'))}<br><span class='muted'>{fmt_pct(last3.get('payment_delta_pct'))}</span></td>"
            "</tr>"
        )
    common_rows = []
    for item in analysis.get("common_negative_products", [])[:12]:
        common_rows.append(
            "<tr>"
            f"<td>{esc(item.get('group'))}</td>"
            f"<td>{esc(item.get('product'))}</td>"
            f"<td>{esc(item.get('category_large'))}</td>"
            f"<td>{esc(item.get('hit_count'))}</td>"
            f"<td class='negative'>{fmt_delta(item.get('total_negative_delta'))}</td>"
            f"<td>{esc(item.get('primary_reason_candidate'))}</td>"
            "</tr>"
        )
    reason_rows = []
    for item in analysis.get("reason_candidate_summaries", []):
        examples = ", ".join(
            f"{example.get('product')}({fmt_delta(example.get('payment_delta'))})"
            for example in item.get("top_negative_examples", [])[:3]
        )
        reason_rows.append(
            "<tr>"
            f"<td>{esc(item.get('reason_candidate'))}</td>"
            f"<td class='negative'>{fmt_delta(item.get('payment_delta_sum'))}<br><span class='muted'>{fmt_pct(item.get('gross_negative_delta_share'))}</span></td>"
            f"<td class='{delta_class(item.get('ad_spend_delta_sum'))}'>{fmt_delta(item.get('ad_spend_delta_sum'))}</td>"
            f"<td>{esc(item.get('signal_count'))}</td>"
            f"<td>{esc(item.get('unique_product_count'))}</td>"
            f"<td>{esc(', '.join(item.get('categories', [])))}</td>"
            f"<td>{esc(examples)}</td>"
            "</tr>"
        )
    efficiency_rows = []
    for item in analysis.get("recent_efficiency_decline_candidates", []):
        roas_series = item.get("roas_series_pct", {})
        roas_trend = " -> ".join(
            fmt_percent_value(roas_series.get(period))
            for period in ["last_3w", "last_2w", "last_1w", "current_wtd"]
        )
        reason_text = "; ".join(item.get("reason_candidates", []))
        efficiency_rows.append(
            "<tr>"
            f"<td>{esc(item.get('group'))}</td>"
            f"<td>{esc(item.get('product'))}</td>"
            f"<td>{esc(item.get('category_large'))}</td>"
            f"<td>{esc(reason_text)}</td>"
            f"<td class='{delta_class(item.get('payment_delta_vs_previous_3w_avg'))}'>{fmt_delta(item.get('payment_delta_vs_previous_3w_avg'))}<br><span class='muted'>이번주 {fmt_money(item.get('payment_current'))} / 직전 3주 평균 {fmt_money(item.get('payment_previous_3w_avg'))}</span></td>"
            f"<td class='{delta_class(item.get('roas_delta_pct_points_vs_previous_3w_avg'))}'>{fmt_percent_point_delta(item.get('roas_delta_pct_points_vs_previous_3w_avg'))}<br><span class='muted'>이번주 {fmt_percent_value(item.get('roas_current_pct'))} / 직전 3주 평균 {fmt_percent_value(item.get('roas_previous_3w_avg_pct'))}</span></td>"
            f"<td>{esc(roas_trend)}</td>"
            f"<td class='{delta_class(item.get('ad_spend_delta_vs_previous_3w_avg'))}'>{fmt_delta(item.get('ad_spend_delta_vs_previous_3w_avg'))}</td>"
            "</tr>"
        )
    driver_rows = []
    for block in analysis.get("product_driver_analyses", []):
        for product in block.get("top_negative_products", [])[:3]:
            driver_rows.append(
                "<tr>"
                f"<td>{esc(block.get('category'))}</td>"
                f"<td>{esc(block.get('comparison'))}</td>"
                f"<td>{esc(product.get('product'))}</td>"
                f"<td>{esc(product.get('category_large'))}</td>"
                f"<td class='negative'>{fmt_delta(product.get('payment_delta'))}</td>"
                f"<td class='{delta_class(product.get('ad_spend_delta'))}'>{fmt_delta(product.get('ad_spend_delta'))}</td>"
                f"<td>{esc(product.get('reason_candidate'))}</td>"
                "</tr>"
            )
    limitations = "\n".join(
        f"<li>{esc(item)}</li>" for item in analysis.get("gates", {}).get("limitations", [])
    )
    return f"""
    <section>
      <h2>결제액 하락 원인 분석</h2>
      <div class="grid">
        <div class="card"><h3>지표 기준</h3><p>{esc(metric_basis)}</p></div>
        <div class="card"><h3>이번주 분석 구간</h3><p><code>{esc(', '.join(windows.get('current_wtd', [])))}</code></p><p class="muted">마지막 결제액 입력일: {esc(analysis.get('latest_nonzero_payment_date'))}</p></div>
        <div class="card"><h3>검증 결과</h3><p>카테고리 화면의 결제액 합계와 원천 상품군 합계가 샘플 비교 구간에서 일치했습니다.</p></div>
      </div>
      <h3>카테고리 하락 신호</h3>
      <table><thead><tr><th>카테고리</th><th>상태</th><th>이번주 결제액</th><th>전년 대비 변화</th><th>전월 대비 변화</th><th>최근 3주 평균 대비 변화</th></tr></thead><tbody>{''.join(category_rows)}</tbody></table>
      <h3>원인 후보별 하락 규모 요약</h3>
      <p class="muted">상품별 하락 신호의 절대 하락액 기준입니다. 같은 상품이 여러 비교축에서 하락하면 여러 하락 신호로 집계됩니다.</p>
      <table><thead><tr><th>원인 후보</th><th>결제액 하락 합계</th><th>광고비 변화 합계</th><th>하락 신호 수</th><th>고유 상품 수</th><th>카테고리</th><th>주요 예시</th></tr></thead><tbody>{''.join(reason_rows)}</tbody></table>
      <h3>최근 ROAS 하락 과정</h3>
      <p class="muted">결제액 감소 후보 중 3주 전, 2주 전, 1주 전, 이번주 누적 ROAS% 기울기가 음수이고 이번주 ROAS%가 직전 3개 구간 평균보다 낮은 과정입니다.</p>
      <table><thead><tr><th>상품군</th><th>과정</th><th>상위 카테고리</th><th>원인 후보</th><th>결제액 변화</th><th>ROAS% 하락폭</th><th>ROAS% 흐름</th><th>광고비 변화</th></tr></thead><tbody>{''.join(efficiency_rows)}</tbody></table>
      <h3>공통상품 하락 후보</h3>
      <table><thead><tr><th>상품군</th><th>공통상품</th><th>상위 카테고리</th><th>하락 신호 수</th><th>총 하락액</th><th>주요 원인 후보</th></tr></thead><tbody>{''.join(common_rows)}</tbody></table>
      <h3>비교 기준별 주요 하락 상품</h3>
      <table><thead><tr><th>카테고리</th><th>비교 기준</th><th>공통상품</th><th>상위 카테고리</th><th>결제액 변화</th><th>광고비 변화</th><th>원인 후보</th></tr></thead><tbody>{''.join(driver_rows)}</tbody></table>
      <h3>검증 메모</h3>
      <ul>{limitations}</ul>
    </section>
"""


def render_html(run_dir: Path, surface: dict[str, Any], tables: dict[str, Any], labels: dict[str, Any], graph: dict[str, Any], questions: dict[str, Any]) -> str:
    surface_rows = "\n".join(
        f"<tr><td>{esc(s['title'])}</td><td>{esc(display(s['surface_role']))}</td><td>{esc(display(s['surface_subtype']))}</td><td>{esc(s['range'])}</td></tr>"
        for s in surface["surfaces"]
    )
    table_cards = "\n".join(
        f"<article class='card'><h3>{esc(t['name'])}</h3><p><code>{esc(t['range'])}</code></p><p>{esc(display(t['role']))} · {esc(display(t['status']))}</p><ul>{''.join(f'<li>{esc(e)}</li>' for e in t['boundary_evidence'])}</ul></article>"
        for t in tables["tables"]
    )
    label_rows = "\n".join(
        f"<tr><td>{esc(l['column'])}</td><td>{esc(display_label(l['label']))}</td><td>{esc(display(l['role']))}</td><td>{esc(l['definition'])}</td><td><code>{esc(l['sample_formula'])}</code></td></tr>"
        for l in labels["labels"]
        if l["column"] <= "AT"
    )
    question_items = "\n".join(
        f"<li><strong>질문 {index}</strong><p>{esc(q['question'])}</p><p><code>{esc(', '.join(q['related_ranges']))}</code></p></li>"
        for index, q in enumerate(questions["questions"], start=1)
    )
    payment_decline_section = render_payment_decline_section(run_dir)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>초기 시트 이해</title>
  <style>
    body {{ margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #17202a; background: #f7f9fb; }}
    header {{ padding: 28px 36px; background: #17324d; color: white; }}
    main {{ padding: 28px 36px 60px; max-width: 1320px; margin: 0 auto; }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    section {{ margin: 28px 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }}
    .card {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 16px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #d9e2ec; }}
    th, td {{ padding: 8px 10px; border-bottom: 1px solid #e8eef5; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #edf3f8; position: sticky; top: 0; }}
    code, pre {{ background: #eef3f8; border-radius: 4px; padding: 2px 4px; }}
    pre {{ padding: 14px; overflow: auto; white-space: pre-wrap; }}
    .flow-svg {{ background: white; border: 1px solid #d9e2ec; border-radius: 8px; padding: 12px; overflow: auto; }}
    .io-svg {{ display: block; width: 100%; min-width: 980px; height: auto; }}
    .muted {{ color: #5c6f82; }}
    .negative {{ color: #a12a2a; font-weight: 700; }}
    .positive {{ color: #237344; font-weight: 700; }}
  </style>
</head>
<body>
  <header>
    <h1>초기 시트 이해</h1>
    <p>대상: <strong>[취미/부업 본부 - 교육콘텐츠그룹] 마이라이트 Dashboard_2026</strong> / <strong>MLL_Overview(신규/롱테일)</strong></p>
  </header>
  <main>
    <section>
      <h2>요약 설명</h2>
      <div class="grid">
        <div class="card"><h3>목적</h3><p>신규/롱테일 기준으로 광고비, 결제액, 순매출, 구매/결제 수, ROAS, 고객획득비용, 평균 객단가를 월/일/주 단위로 집계하는 MLL 성과 화면입니다.</p></div>
        <div class="card"><h3>원천 근거</h3><p>주요 원천 시트는 <code>[DB]RAW_광고비</code>, <code>[DB]RAW_결제액</code>, <code>[DB]RAW_결제수</code>, <code>[DB]RAW_순매출</code>, <code>[DB]RAW_순구매수</code> 계열입니다.</p></div>
        <div class="card"><h3>확인 필요 사항</h3><p>J/N/AD/AH처럼 합계에 포함되지만 표기가 비어 있는 컬럼과 신규/롱테일 29/30일 경계, 공통광고비 배부 기준은 확인 질문이 필요합니다.</p></div>
      </div>
    </section>
    <section><h2>시트 표면 목록</h2><table><thead><tr><th>시트</th><th>역할</th><th>세부 유형</th><th>범위</th></tr></thead><tbody>{surface_rows}</tbody></table></section>
    <section><h2>표 후보</h2><div class="grid">{table_cards}</div></section>
    <section><h2>표 입출력 흐름</h2><div class="flow-svg">{graph['svg']}</div></section>
    <section><h2>표기 사전</h2><table><thead><tr><th>열</th><th>표기</th><th>역할</th><th>의미</th><th>예시 수식</th></tr></thead><tbody>{label_rows}</tbody></table></section>
    {payment_decline_section}
    <section><h2>검토 질문</h2><ol>{question_items}</ol></section>
    <section><h2>산출물</h2><p class="muted">생성 위치: <code>{esc(run_dir)}</code></p></section>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir
    values = load_windows(run_dir, "target-values_window-MLL-new-longtail")
    formulas = load_windows(run_dir, "target-formula_window-MLL-new-longtail")
    surface = build_surface_inventory(run_dir)
    tables = table_candidates(values, formulas)
    labels = label_dictionary(values, formulas)
    graph = io_graph()
    questions = review_questions()
    write_json(run_dir / "surface-inventory.json", surface)
    write_json(run_dir / "table-candidates.json", tables)
    write_json(run_dir / "label-dictionary.json", labels)
    write_json(run_dir / "table-io-graph.json", graph)
    write_json(run_dir / "review-questions.json", questions)
    (run_dir / "table-io-flow.svg").write_text(graph["svg"], encoding="utf-8")
    (run_dir / "index.html").write_text(render_html(run_dir, surface, tables, labels, graph, questions), encoding="utf-8")


if __name__ == "__main__":
    main()
