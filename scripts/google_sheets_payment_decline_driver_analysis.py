#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any


CATEGORIES = ["취미", "부업", "커리어/재테크", "그외"]
PAYMENT_COLUMNS = {"취미": 9, "부업": 10, "커리어/재테크": 11, "그외": 12}
AD_SPEND_COLUMNS = {"취미": 3, "부업": 4, "커리어/재테크": 5, "그외": 6, "공통광고비": 7}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def payload_windows(path: Path) -> list[dict[str, Any]]:
    return read_json(path).get("payload", {}).get("windows", [])


def parse_number(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "#N/A", "#DIV/0!", "#VALUE!"}:
        return 0.0
    if text.endswith("%"):
        text = text[:-1]
    text = text.replace(",", "").replace("₩", "")
    try:
        return float(text)
    except ValueError:
        return 0.0


def load_category_rows(run_dir: Path) -> dict[date, dict[str, Any]]:
    by_date: dict[date, dict[str, Any]] = {}
    for path in sorted(run_dir.glob("category-values_window-MLL-category-*.json")):
        for window in payload_windows(path):
            match = re.search(r"A(\d+):", window.get("range", ""))
            if not match:
                continue
            start_row = int(match.group(1))
            for row_index, row in enumerate(window.get("values", []), start_row):
                if not row:
                    continue
                label = str(row[0])
                if re.fullmatch(r"\d{4}-\d{2}-\d{2}", label):
                    by_date[date.fromisoformat(label)] = {"row": row_index, "values": row}
    return by_date


def latest_nonzero_payment_date(by_date: dict[date, dict[str, Any]]) -> date:
    candidates = []
    for day, record in by_date.items():
        row = record["values"]
        total_payment = parse_number(row[8] if len(row) > 8 else 0)
        if total_payment > 0:
            candidates.append(day)
    if not candidates:
        raise ValueError("No nonzero category payment date was found.")
    return max(candidates)


def inclusive_dates(start: date, end: date) -> list[date]:
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def comparison_windows(latest: date) -> dict[str, list[date]]:
    current_start = latest - timedelta(days=latest.weekday())
    window_length = (latest - current_start).days + 1
    previous_month_start = current_start - timedelta(days=28)
    yoy_start = current_start - timedelta(days=364)
    windows = {
        "current_wtd": inclusive_dates(current_start, latest),
        "mom_same_weekday": inclusive_dates(
            previous_month_start,
            previous_month_start + timedelta(days=window_length - 1),
        ),
        "yoy_same_weekday": inclusive_dates(yoy_start, yoy_start + timedelta(days=window_length - 1)),
    }
    for index in range(1, 4):
        start = current_start - timedelta(days=7 * index)
        windows[f"last_{index}w"] = inclusive_dates(start, start + timedelta(days=window_length - 1))
    return windows


def sum_category(
    by_date: dict[date, dict[str, Any]],
    columns: dict[str, int],
    days: list[date],
) -> dict[str, float]:
    result = {key: 0.0 for key in columns}
    for day in days:
        row = by_date.get(day, {}).get("values", [])
        for key, column in columns.items():
            result[key] += parse_number(row[column] if column < len(row) else 0)
    return result


def load_raw_meta(run_dir: Path) -> list[dict[str, Any]]:
    meta_path = run_dir / "raw-date-header-and-meta-values.json"
    for window in payload_windows(meta_path):
        if window.get("range") == "'[DB]RAW_결제액-필터금지'!A1:D1000":
            products = []
            for row_index, row in enumerate(window.get("values", []), start=1):
                if row_index < 3 or len(row) < 2 or not row[1]:
                    continue
                products.append(
                    {
                        "row": row_index,
                        "launch_date": row[0] if len(row) > 0 else "",
                        "product": row[1] if len(row) > 1 else "",
                        "group": row[2] if len(row) > 2 else "",
                        "category_large": row[3] if len(row) > 3 else "",
                    }
                )
            return products
    raise ValueError("RAW payment product metadata window was not found.")


def load_raw_metric_values(run_dir: Path) -> dict[str, dict[date, dict[int, float]]]:
    values: dict[str, dict[date, dict[int, float]]] = {}
    comparison_path = run_dir / "raw-payment-ad-comparison-windows-values.json"
    for window in payload_windows(comparison_path):
        metric = "payment" if "결제액" in window.get("range", "") else "ad_spend"
        rows = window.get("values", [])
        if len(rows) < 2:
            continue
        dates = [date.fromisoformat(value) for value in rows[1]]
        for row_index, row in enumerate(rows, start=1):
            for offset, day in enumerate(dates):
                values.setdefault(metric, {}).setdefault(day, {})[row_index] = parse_number(
                    row[offset] if offset < len(row) else 0
                )
    return values


def product_sum(
    raw_values: dict[str, dict[date, dict[int, float]]],
    metric: str,
    product: dict[str, Any],
    days: list[date],
) -> float:
    return sum(raw_values.get(metric, {}).get(day, {}).get(product["row"], 0.0) for day in days)


def ratio(current: float, baseline: float) -> float | None:
    if abs(baseline) < 1e-9:
        return None
    return (current - baseline) / baseline


def roas(payment: float, ad_spend: float) -> float | None:
    if ad_spend <= 0:
        return None
    return payment / ad_spend


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def linear_slope(points: list[tuple[int, float]]) -> float | None:
    if len(points) < 2:
        return None
    mean_x = sum(point[0] for point in points) / len(points)
    mean_y = sum(point[1] for point in points) / len(points)
    denominator = sum((point[0] - mean_x) ** 2 for point in points)
    if denominator == 0:
        return None
    return sum((point[0] - mean_x) * (point[1] - mean_y) for point in points) / denominator


def baseline_value(series: dict[str, float], comparison: str) -> float:
    if comparison == "전년도 대비":
        return series["yoy_same_weekday"]
    if comparison == "전월 대비":
        return series["mom_same_weekday"]
    if comparison == "지난 3주 평균 대비":
        return (series["last_1w"] + series["last_2w"] + series["last_3w"]) / 3
    raise ValueError(f"Unknown comparison: {comparison}")


def classify_reason(payment_current: float, payment_baseline: float, ad_current: float, ad_baseline: float) -> str:
    payment_delta = payment_current - payment_baseline
    if payment_delta >= 0:
        return "결제액 하락 아님"
    if ad_baseline <= 0 and ad_current <= 0:
        return "광고비 근거 없음: 상품별 광고비 0/미검출, 수요·전환·상품/가격·채널 믹스 확인 필요"
    if ad_current > ad_baseline * 1.05:
        return "광고비 증가에도 결제액 하락: 효율/전환/상품 수요 문제 가능성"
    if ad_current >= ad_baseline * 0.9:
        return "광고비 유지권인데 결제액 하락: 효율/전환/상품 수요 문제 가능성"
    current_roas = roas(payment_current, ad_current)
    baseline_roas = roas(payment_baseline, ad_baseline)
    if current_roas and baseline_roas:
        if current_roas >= baseline_roas * 0.9:
            return "광고비 하락 가능성 높음: ROAS는 유지/개선권"
        if current_roas < baseline_roas * 0.75:
            return "혼합: 광고비도 줄었지만 ROAS도 크게 악화"
    return "광고비 하락 일부 가능성: 효율 변화 추가 확인 필요"


def analyze(run_dir: Path) -> dict[str, Any]:
    by_date = load_category_rows(run_dir)
    latest = latest_nonzero_payment_date(by_date)
    windows = comparison_windows(latest)
    category_payment = {name: sum_category(by_date, PAYMENT_COLUMNS, days) for name, days in windows.items()}
    category_ad = {name: sum_category(by_date, AD_SPEND_COLUMNS, days) for name, days in windows.items()}
    products = load_raw_meta(run_dir)
    raw_values = load_raw_metric_values(run_dir)

    for product in products:
        product["payment"] = {
            name: product_sum(raw_values, "payment", product, days) for name, days in windows.items()
        }
        product["ad_spend"] = {
            name: product_sum(raw_values, "ad_spend", product, days) for name, days in windows.items()
        }

    comparisons = ["전년도 대비", "전월 대비", "지난 3주 평균 대비"]
    category_summaries = []
    for category in CATEGORIES:
        comparison_rows = []
        declining_count = 0
        for comparison in comparisons:
            current_payment = category_payment["current_wtd"][category]
            baseline_payment = baseline_value({key: value[category] for key, value in category_payment.items()}, comparison)
            current_ad = category_ad["current_wtd"][category]
            baseline_ad = baseline_value({key: value[category] for key, value in category_ad.items()}, comparison)
            payment_delta = current_payment - baseline_payment
            if payment_delta < 0:
                declining_count += 1
            comparison_rows.append(
                {
                    "comparison": comparison,
                    "baseline_payment": baseline_payment,
                    "current_payment": current_payment,
                    "payment_delta": payment_delta,
                    "payment_delta_pct": ratio(current_payment, baseline_payment),
                    "baseline_ad_spend": baseline_ad,
                    "current_ad_spend": current_ad,
                    "ad_spend_delta": current_ad - baseline_ad,
                    "ad_spend_delta_pct": ratio(current_ad, baseline_ad),
                }
            )
        category_summaries.append(
            {
                "category": category,
                "current_payment": category_payment["current_wtd"][category],
                "declining_signal_count": declining_count,
                "status": "multi_signal_decline"
                if declining_count >= 2
                else ("single_signal_decline" if declining_count == 1 else "not_declining"),
                "comparisons": comparison_rows,
            }
        )

    product_driver_analyses = []
    all_negative_product_signals = []
    for summary in category_summaries:
        category = summary["category"]
        for comparison_row in summary["comparisons"]:
            if comparison_row["payment_delta"] >= 0:
                continue
            comparison = comparison_row["comparison"]
            negative_products = []
            for product in products:
                if product["group"] != category:
                    continue
                current_payment = product["payment"]["current_wtd"]
                baseline_payment = baseline_value(product["payment"], comparison)
                payment_delta = current_payment - baseline_payment
                if payment_delta >= 0:
                    continue
                current_ad = product["ad_spend"]["current_wtd"]
                baseline_ad = baseline_value(product["ad_spend"], comparison)
                signal = {
                    "row": product["row"],
                    "product": product["product"],
                    "group": product["group"],
                    "category_large": product["category_large"],
                    "launch_date": product["launch_date"],
                    "current_payment": current_payment,
                    "baseline_payment": baseline_payment,
                    "payment_delta": payment_delta,
                    "category_delta_share": abs(payment_delta) / abs(comparison_row["payment_delta"])
                    if comparison_row["payment_delta"]
                    else None,
                    "current_ad_spend": current_ad,
                    "baseline_ad_spend": baseline_ad,
                    "ad_spend_delta": current_ad - baseline_ad,
                    "current_roas": roas(current_payment, current_ad),
                    "baseline_roas": roas(baseline_payment, baseline_ad),
                    "reason_candidate": classify_reason(
                        current_payment,
                        baseline_payment,
                        current_ad,
                        baseline_ad,
                    ),
                    "comparison": comparison,
                    "category": category,
                }
                negative_products.append(signal)
                all_negative_product_signals.append(signal)
            negative_products.sort(key=lambda item: item["payment_delta"])
            product_driver_analyses.append(
                {
                    "category": category,
                    "comparison": comparison,
                    "category_payment_delta": comparison_row["payment_delta"],
                    "category_current_payment": comparison_row["current_payment"],
                    "category_baseline_payment": comparison_row["baseline_payment"],
                    "top_negative_products": negative_products[:12],
                    "negative_product_count": len(negative_products),
                    "negative_product_delta_sum": sum(item["payment_delta"] for item in negative_products),
                }
            )

    common_products = defaultdict(
        lambda: {
            "product": None,
            "group": None,
            "category_large": None,
            "hit_count": 0,
            "total_negative_delta": 0.0,
            "comparisons": [],
            "reason_counts": defaultdict(int),
            "current_ad_spend": 0.0,
            "baseline_ad_spend": 0.0,
        }
    )
    for analysis in product_driver_analyses:
        for product in analysis["top_negative_products"][:8]:
            key = (product["group"], product["product"])
            item = common_products[key]
            item["product"] = product["product"]
            item["group"] = product["group"]
            item["category_large"] = product["category_large"]
            item["hit_count"] += 1
            item["total_negative_delta"] += product["payment_delta"]
            item["current_ad_spend"] += product["current_ad_spend"]
            item["baseline_ad_spend"] += product["baseline_ad_spend"]
            item["reason_counts"][product["reason_candidate"]] += 1
            item["comparisons"].append(
                {
                    "category": analysis["category"],
                    "comparison": analysis["comparison"],
                    "payment_delta": product["payment_delta"],
                    "reason_candidate": product["reason_candidate"],
                }
            )

    common_negative_products = []
    for item in common_products.values():
        item["reason_counts"] = dict(item["reason_counts"])
        item["primary_reason_candidate"] = max(item["reason_counts"].items(), key=lambda pair: pair[1])[0]
        common_negative_products.append(item)
    common_negative_products.sort(key=lambda item: (-item["hit_count"], item["total_negative_delta"]))

    reason_summaries: dict[str, dict[str, Any]] = {}
    for signal in all_negative_product_signals:
        reason = signal["reason_candidate"]
        summary = reason_summaries.setdefault(
            reason,
            {
                "reason_candidate": reason,
                "signal_count": 0,
                "unique_products": set(),
                "categories": set(),
                "payment_delta_sum": 0.0,
                "current_payment_sum": 0.0,
                "baseline_payment_sum": 0.0,
                "ad_spend_delta_sum": 0.0,
                "current_ad_spend_sum": 0.0,
                "baseline_ad_spend_sum": 0.0,
                "top_negative_examples": [],
            },
        )
        summary["signal_count"] += 1
        summary["unique_products"].add((signal["group"], signal["product"]))
        summary["categories"].add(signal["category"])
        summary["payment_delta_sum"] += signal["payment_delta"]
        summary["current_payment_sum"] += signal["current_payment"]
        summary["baseline_payment_sum"] += signal["baseline_payment"]
        summary["ad_spend_delta_sum"] += signal["ad_spend_delta"]
        summary["current_ad_spend_sum"] += signal["current_ad_spend"]
        summary["baseline_ad_spend_sum"] += signal["baseline_ad_spend"]
        summary["top_negative_examples"].append(
            {
                "category": signal["category"],
                "comparison": signal["comparison"],
                "product": signal["product"],
                "payment_delta": signal["payment_delta"],
                "ad_spend_delta": signal["ad_spend_delta"],
            }
        )

    gross_negative_delta = sum(item["payment_delta_sum"] for item in reason_summaries.values())
    reason_candidate_summaries = []
    for summary in reason_summaries.values():
        examples = sorted(summary["top_negative_examples"], key=lambda item: item["payment_delta"])[:5]
        payment_delta_sum = summary["payment_delta_sum"]
        reason_candidate_summaries.append(
            {
                "reason_candidate": summary["reason_candidate"],
                "signal_count": summary["signal_count"],
                "unique_product_count": len(summary["unique_products"]),
                "categories": sorted(summary["categories"]),
                "payment_delta_sum": payment_delta_sum,
                "gross_negative_delta_share": abs(payment_delta_sum) / abs(gross_negative_delta)
                if gross_negative_delta
                else None,
                "current_payment_sum": summary["current_payment_sum"],
                "baseline_payment_sum": summary["baseline_payment_sum"],
                "ad_spend_delta_sum": summary["ad_spend_delta_sum"],
                "current_ad_spend_sum": summary["current_ad_spend_sum"],
                "baseline_ad_spend_sum": summary["baseline_ad_spend_sum"],
                "top_negative_examples": examples,
            }
        )
    reason_candidate_summaries.sort(key=lambda item: item["payment_delta_sum"])

    negative_signal_meta: dict[tuple[str, str], dict[str, Any]] = {}
    for signal in all_negative_product_signals:
        key = (signal["group"], signal["product"])
        meta = negative_signal_meta.setdefault(
            key,
            {"signal_count": 0, "reason_candidates": set(), "comparisons": set()},
        )
        meta["signal_count"] += 1
        meta["reason_candidates"].add(signal["reason_candidate"])
        meta["comparisons"].add(signal["comparison"])

    trend_periods = ["last_3w", "last_2w", "last_1w", "current_wtd"]
    recent_efficiency_decline_candidates = []
    for product in products:
        key = (product["group"], product["product"])
        if key not in negative_signal_meta:
            continue
        roas_series_pct = {}
        payment_series = {}
        ad_spend_series = {}
        valid_roas_points = []
        for index, period in enumerate(trend_periods):
            period_payment = product["payment"][period]
            period_ad_spend = product["ad_spend"][period]
            period_roas = roas(period_payment, period_ad_spend)
            payment_series[period] = period_payment
            ad_spend_series[period] = period_ad_spend
            roas_series_pct[period] = period_roas * 100 if period_roas is not None else None
            if period_roas is not None:
                valid_roas_points.append((index, period_roas * 100))

        prior_periods = ["last_3w", "last_2w", "last_1w"]
        prior_roas_values = [
            roas_series_pct[period] for period in prior_periods if roas_series_pct[period] is not None
        ]
        current_roas_pct = roas_series_pct["current_wtd"]
        prior_roas_avg_pct = average(prior_roas_values)
        roas_slope_pct_per_period = linear_slope(valid_roas_points)
        current_payment = payment_series["current_wtd"]
        prior_payment_avg = average([payment_series[period] for period in prior_periods]) or 0.0
        current_ad_spend = ad_spend_series["current_wtd"]
        prior_ad_spend_avg = average([ad_spend_series[period] for period in prior_periods]) or 0.0
        roas_delta_pct_points = (
            current_roas_pct - prior_roas_avg_pct
            if current_roas_pct is not None and prior_roas_avg_pct is not None
            else None
        )
        is_declining = (
            len(valid_roas_points) >= 3
            and current_roas_pct is not None
            and prior_roas_avg_pct is not None
            and roas_slope_pct_per_period is not None
            and roas_slope_pct_per_period < 0
            and current_roas_pct < prior_roas_avg_pct
        )
        if not is_declining:
            continue
        meta = negative_signal_meta[key]
        recent_efficiency_decline_candidates.append(
            {
                "product": product["product"],
                "group": product["group"],
                "category_large": product["category_large"],
                "negative_signal_count": meta["signal_count"],
                "reason_candidates": sorted(meta["reason_candidates"]),
                "comparisons": sorted(meta["comparisons"]),
                "payment_current": current_payment,
                "payment_previous_3w_avg": prior_payment_avg,
                "payment_delta_vs_previous_3w_avg": current_payment - prior_payment_avg,
                "payment_delta_pct_vs_previous_3w_avg": ratio(current_payment, prior_payment_avg),
                "ad_spend_current": current_ad_spend,
                "ad_spend_previous_3w_avg": prior_ad_spend_avg,
                "ad_spend_delta_vs_previous_3w_avg": current_ad_spend - prior_ad_spend_avg,
                "roas_current_pct": current_roas_pct,
                "roas_previous_3w_avg_pct": prior_roas_avg_pct,
                "roas_delta_pct_points_vs_previous_3w_avg": roas_delta_pct_points,
                "roas_slope_pct_points_per_period": roas_slope_pct_per_period,
                "roas_series_pct": roas_series_pct,
                "payment_series": payment_series,
                "ad_spend_series": ad_spend_series,
                "valid_roas_point_count": len(valid_roas_points),
                "trend_gate": "pass",
            }
        )
    recent_efficiency_decline_candidates.sort(
        key=lambda item: (
            item["payment_delta_vs_previous_3w_avg"],
            item["roas_delta_pct_points_vs_previous_3w_avg"],
        )
    )

    raw_category_sums: dict[str, dict[str, float]] = {}
    for window_name in windows:
        raw_category_sums[window_name] = defaultdict(float)
        for product in products:
            raw_category_sums[window_name][product["group"]] += product["payment"][window_name]
    validation = []
    for window_name in windows:
        for category in CATEGORIES:
            raw_sum = raw_category_sums[window_name][category]
            dashboard_sum = category_payment[window_name][category]
            validation.append(
                {
                    "window": window_name,
                    "category": category,
                    "dashboard_payment": dashboard_sum,
                    "raw_payment_by_group": raw_sum,
                    "delta": raw_sum - dashboard_sum,
                    "status": "pass" if abs(raw_sum - dashboard_sum) < 1 else "review",
                }
            )

    return {
        "artifact_type": "payment_decline_driver_analysis_v0_1",
        "source": {
            "spreadsheet_id": "1G07-jmsFWiWYtB5E08puFHlBVuyBf488Ae12BkEmsbs",
            "target_sheet": "MLL_Overview(카테고리)",
            "raw_payment_sheet": "[DB]RAW_결제액-필터금지",
            "raw_ad_spend_sheet": "[DB]RAW_광고비-필터금지",
            "metric_basis": "user-confirmed payment amount / 결제액, not accounting revenue",
        },
        "comparison_windows": {name: [day.isoformat() for day in days] for name, days in windows.items()},
        "latest_nonzero_payment_date": latest.isoformat(),
        "category_summaries": category_summaries,
        "product_driver_analyses": product_driver_analyses,
        "common_negative_products": common_negative_products[:20],
        "reason_candidate_summaries": reason_candidate_summaries,
        "recent_efficiency_decline_candidates": recent_efficiency_decline_candidates,
        "gates": {
            "dashboard_vs_raw_category_payment": validation,
            "limitations": [
                f"이번주 값은 {windows['current_wtd'][0].isoformat()}~{windows['current_wtd'][-1].isoformat()} 누적 기준이며 이후 0 표시 날짜는 현재 분석에서 제외했다.",
                "광고비 원인 판정은 RAW 상품별 개별 광고비 기준이다. 공통광고비 배부 로직은 상품/카테고리별로 확정하지 않았다.",
                "전월 대비는 달력상 전월 전체가 아니라 같은 요일 길이의 4주 전 비교로 정의했다.",
                "전년 대비는 같은 요일 길이의 52주 전 비교로 정의했다.",
            ],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.run_dir / "payment-decline-driver-analysis.json"
    write_json(output, analyze(args.run_dir))


if __name__ == "__main__":
    main()
