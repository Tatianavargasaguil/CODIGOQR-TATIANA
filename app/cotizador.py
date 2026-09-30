import hashlib
import json
import os
import re
import sqlite3
import unicodedata
from datetime import datetime, timedelta
from difflib import get_close_matches
from functools import lru_cache
from pathlib import Path
from typing import Any

import requests


DATA_DIR = Path(__file__).resolve().parent / "cotizador_data"
CACHE_DB = Path(__file__).resolve().parent.parent / "cotizador_cache.db"
QUOTE_RANGE_WIDTH = 5_000_000
DIRECTOR_REVIEW_THRESHOLD = 160_000_000


class CotizadorError(Exception):
    pass


def normalize_key(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", text.upper()).strip()


def sanitize_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return int(round(value))
    text = re.sub(r"[^\d-]", "", str(value))
    if not text or text == "-":
        return default
    try:
        return int(text)
    except ValueError:
        return default


def format_cop(value: Any) -> str:
    return f"$ {to_int(value):,}".replace(",", ".")


def sanitize_plate(value: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", normalize_key(value))


@lru_cache(maxsize=None)
def load_json_file(filename: str) -> Any:
    path = DATA_DIR / filename
    if not path.exists():
        return [] if filename.endswith("catalog.json") else {}
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def get_options_index() -> dict[str, Any]:
    data = load_json_file("options-index.json")
    return data if isinstance(data, dict) else {}


@lru_cache(maxsize=None)
def get_known_brands() -> tuple[str, ...]:
    brands = set(get_options_index().keys())
    for kind in ("new", "used"):
        for item in get_catalog(kind):
            brand = normalize_key(item.get("brand"))
            if brand:
                brands.add(brand)
    return tuple(sorted(brands))


def resolve_brand(value: Any) -> str:
    brand = normalize_key(value)
    if not brand:
        return ""
    known_brands = get_known_brands()
    if brand in known_brands:
        return brand
    matches = get_close_matches(brand, known_brands, n=1, cutoff=0.78)
    return matches[0] if matches else brand


def get_versions_index() -> dict[str, Any]:
    data = load_json_file("versions-index.json")
    return data if isinstance(data, dict) else {}


def get_year_options() -> list[int]:
    current_year = datetime.utcnow().year
    return list(range(current_year + 1, 1979, -1))


def get_catalog(kind: str) -> list[dict[str, Any]]:
    filename = "new-scraping-catalog.json" if kind == "new" else "used-scraping-catalog.json"
    data = load_json_file(filename)
    return data if isinstance(data, list) else []


def tokens(*values: Any) -> set[str]:
    text = normalize_key(" ".join(sanitize_text(v) for v in values))
    return {t for t in re.split(r"[^A-Z0-9]+", text) if len(t) > 1}


def canonical_reference(brand: str, line: str, version: str = "") -> str:
    parts = sorted(tokens(brand, line, version))
    return " ".join(parts)


def reference_score(item: dict[str, Any], brand: str, line: str, version: str, year: int) -> int:
    wanted_brand = normalize_key(brand)
    wanted = tokens(line, version)
    item_brand = normalize_key(item.get("brand"))
    item_tokens = tokens(item.get("model"), item.get("version"))

    score = 0
    if item_brand == wanted_brand:
        score += 80
    elif wanted_brand and (wanted_brand in item_brand or item_brand in wanted_brand):
        score += 35

    score += len(wanted & item_tokens) * 18
    item_year = to_int(item.get("year"))
    if item_year:
        diff = abs(item_year - year)
        if diff == 0:
            score += 30
        elif diff == 1:
            score += 18
        elif diff == 2:
            score += 8

    return score


def score_market_references(kind: str, brand: str, line: str, version: str, year: int) -> list[dict[str, Any]]:
    scored = []
    for item in get_catalog(kind):
        price = to_int(item.get("price"))
        if price <= 0:
            continue
        score = reference_score(item, brand, line, version, year)
        if score < 80:
            continue
        enriched = dict(item)
        enriched["_score"] = score
        scored.append(enriched)
    scored.sort(key=lambda x: (-x["_score"], abs(to_int(x.get("year")) - year), to_int(x.get("price"))))
    return scored[:80]


def public_market_reference(item: dict[str, Any], kind: str) -> dict[str, Any]:
    return {
        "platform": sanitize_text(item.get("platform")) or ("NUEVO" if kind == "new" else "USADO"),
        "vehicle": " ".join(
            p for p in [
                sanitize_text(item.get("brand")),
                sanitize_text(item.get("model")),
                sanitize_text(item.get("version")),
            ] if p and p != "-"
        ),
        "year": to_int(item.get("year")),
        "price": to_int(item.get("price")),
        "price_formatted": format_cop(item.get("price")),
        "city": sanitize_text(item.get("city")) or "-",
        "seller": sanitize_text(item.get("seller")) or "-",
        "url": sanitize_text(item.get("url")),
    }


def find_market_references(kind: str, brand: str, line: str, version: str, year: int) -> list[dict[str, Any]]:
    return [public_market_reference(item, kind) for item in score_market_references(kind, brand, line, version, year)[:50]]


def median_int(values: list[int]) -> int:
    values = sorted(v for v in values if v > 0)
    if not values:
        return 0
    mid = len(values) // 2
    if len(values) % 2:
        return values[mid]
    return int(round((values[mid - 1] + values[mid]) / 2))


def get_offer_range(offer: int) -> tuple[int, int]:
    center = max(0, to_int(offer))
    half = QUOTE_RANGE_WIDTH // 2
    return max(0, center - half), center + half


def is_electric_vehicle(features: dict[str, Any]) -> bool:
    fuel = normalize_key(features.get("fuel") or features.get("combustible"))
    return any(word in fuel for word in ("ELECTRICO", "ELECTRICA", "EV"))


def market_purchase_percent(age: int, mileage: int, electric: bool) -> float:
    if electric:
        base = 0.58 if age <= 1 else 0.52
    elif age <= 1:
        base = 0.80
    else:
        base = 0.77
    if mileage >= 120_000:
        base -= 0.08
    elif mileage >= 80_000:
        base -= 0.05
    elif mileage >= 50_000:
        base -= 0.025
    return max(0.45, min(base, 0.82))


def quote_cache_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def quote_cache_expires_at() -> str:
    tomorrow = datetime.now().date() + timedelta(days=1)
    return datetime.combine(tomorrow, datetime.min.time()).isoformat()


def quote_cache_key(brand: str, line: str, year: int, mileage: int, version: str, features: dict[str, Any]) -> str:
    plate = sanitize_plate(features.get("plate") or features.get("placa"))
    if plate:
        basis = {"plate": plate, "date": quote_cache_date()}
    else:
        basis = {
            "brand": normalize_key(brand),
            "reference": canonical_reference(brand, line, version),
            "year": to_int(year),
            "mileage_bucket": int(to_int(mileage) / 5000) * 5000,
            "fuel": normalize_key(features.get("fuel") or features.get("combustible")),
            "transmission": normalize_key(features.get("transmission") or features.get("transmision")),
            "traction": normalize_key(features.get("traction") or features.get("traccion")),
            "date": quote_cache_date(),
        }
    return hashlib.sha256(json.dumps(basis, sort_keys=True).encode("utf-8")).hexdigest()


def ensure_cache_table() -> None:
    with sqlite3.connect(CACHE_DB) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS quote_cache (
                cache_key TEXT PRIMARY KEY,
                quote TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_cached_quote(cache_key: str) -> dict[str, Any] | None:
    ensure_cache_table()
    now = datetime.utcnow().isoformat()
    with sqlite3.connect(CACHE_DB) as conn:
        row = conn.execute(
            "SELECT quote FROM quote_cache WHERE cache_key = ? AND expires_at > ?",
            (cache_key, now),
        ).fetchone()
    if not row:
        return None
    try:
        quote = json.loads(row[0])
        quote["cache_hit"] = True
        return quote
    except json.JSONDecodeError:
        return None


def save_cached_quote(cache_key: str, quote_data: dict[str, Any]) -> None:
    ensure_cache_table()
    payload = dict(quote_data)
    payload.pop("cache_hit", None)
    with sqlite3.connect(CACHE_DB) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO quote_cache (cache_key, quote, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (cache_key, json.dumps(payload, ensure_ascii=False), datetime.utcnow().isoformat(), quote_cache_expires_at()),
        )
        conn.commit()


def build_director_review_quote(reference_price: int, reason: str) -> dict[str, Any]:
    return {
        "director_review": True,
        "reference_price": reference_price,
        "reference_price_formatted": format_cop(reference_price) if reference_price else "No encontrado",
        "estimated_sale": 0,
        "estimated_sale_formatted": "Validar con director",
        "mileage_adjustment": 0,
        "mileage_adjustment_formatted": "$ 0",
        "offer_min": 0,
        "offer_max": 0,
        "offer_min_formatted": "Validar",
        "offer_max_formatted": "con director",
        "method": "Validacion manual requerida.",
        "notes": [reason],
    }


def calculate_local_quote(brand: str, line: str, year: int, mileage: int, version: str, features: dict[str, Any]) -> dict[str, Any]:
    new_refs = score_market_references("new", brand, line, version, year)
    used_refs = score_market_references("used", brand, line, version, year)

    new_price = median_int([to_int(item.get("price")) for item in new_refs[:8]])
    used_price = median_int([to_int(item.get("price")) for item in used_refs[:12]])
    reference_price = new_price or used_price

    if reference_price >= DIRECTOR_REVIEW_THRESHOLD:
        return build_director_review_quote(reference_price, "Vehiculo superior a $160.000.000. Validar compra con director.")

    if not reference_price:
        raise CotizadorError("No se encontro una referencia suficiente para calcular la oferta.")

    age = max(0, datetime.utcnow().year - to_int(year))
    electric = is_electric_vehicle(features)
    estimated_sale = used_price or int(round(reference_price * (0.72 if age <= 1 else 0.67)))
    offer = int(round(estimated_sale * market_purchase_percent(age, mileage, electric)))

    if mileage >= 120_000:
        mileage_adjustment = -10_000_000
    elif mileage >= 80_000:
        mileage_adjustment = -8_000_000
    elif mileage >= 50_000:
        mileage_adjustment = -4_000_000
    else:
        mileage_adjustment = 0
    offer = max(0, offer + mileage_adjustment)
    offer_min, offer_max = get_offer_range(offer)

    notes = []
    if mileage >= 80_000:
        notes.append("Kilometraje alto. Revisar estado mecanico antes de comprar.")
    if electric:
        notes.append("Vehiculo electrico: validar bateria, garantia y autonomia.")
    notes.append("Valor sujeto a inspeccion y validacion comercial.")

    return {
        "director_review": False,
        "reference_price": reference_price,
        "reference_price_formatted": format_cop(reference_price),
        "estimated_sale": estimated_sale,
        "estimated_sale_formatted": format_cop(estimated_sale),
        "mileage_adjustment": mileage_adjustment,
        "mileage_adjustment_formatted": format_cop(mileage_adjustment),
        "offer_min": offer_min,
        "offer_max": offer_max,
        "offer_min_formatted": format_cop(offer_min),
        "offer_max_formatted": format_cop(offer_max),
        "method": "IA + referencias de mercado y regla comercial.",
        "notes": notes,
        "comparables": len(new_refs) + len(used_refs),
    }


def calculate_deepseek_quote(brand: str, line: str, year: int, mileage: int, version: str, features: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("CARMAX_DEEPSEEK_API_KEY") or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return calculate_local_quote(brand, line, year, mileage, version, features)

    local_quote = calculate_local_quote(brand, line, year, mileage, version, features)
    if local_quote.get("director_review"):
        return local_quote

    prompt = {
        "vehiculo": {"marca": brand, "linea": line, "version": version, "modelo": year, "kilometraje": mileage},
        "caracteristicas": features,
        "referencia_local": local_quote,
        "instrucciones": "Devuelve solo JSON con los mismos campos. No superes el precio de mercado local y conserva rango de 5 millones.",
    }
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "Eres un analista comercial de compra de usados en Colombia. Responde solo JSON."},
                    {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                ],
                "temperature": 0.1,
            },
            timeout=25,
        )
        if response.status_code >= 400:
            return local_quote
        content = response.json()["choices"][0]["message"]["content"]
        match = re.search(r"\{.*\}", content, flags=re.S)
        if not match:
            return local_quote
        quote_data = json.loads(match.group(0))
        if not isinstance(quote_data, dict):
            return local_quote
        merged = {**local_quote, **quote_data}
        offer_min, offer_max = get_offer_range(to_int(merged.get("offer") or merged.get("offer_min") or local_quote["offer_min"]))
        merged["offer_min"] = offer_min
        merged["offer_max"] = offer_max
        merged["offer_min_formatted"] = format_cop(offer_min)
        merged["offer_max_formatted"] = format_cop(offer_max)
        return merged
    except Exception:
        return local_quote


def quote(payload: dict[str, Any]) -> dict[str, Any]:
    brand = resolve_brand(payload.get("brand"))
    line = normalize_key(payload.get("line"))
    version = normalize_key(payload.get("version"))
    year = to_int(payload.get("year"))
    mileage = to_int(payload.get("mileage"))
    features = payload.get("features") if isinstance(payload.get("features"), dict) else {}

    if not brand or not line or not year:
        raise CotizadorError("Faltan marca, linea o modelo.")

    cache_key = quote_cache_key(brand, line, year, mileage, version, features)
    cached = get_cached_quote(cache_key)
    if cached:
        return cached

    result = calculate_deepseek_quote(brand, line, year, mileage, version, features)
    result["vehicle"] = {
        "brand": brand,
        "line": line,
        "version": version,
        "year": year,
        "mileage": mileage,
    }
    save_cached_quote(cache_key, result)
    result["cache_hit"] = False
    return result


def market_response(kind: str, params: dict[str, Any]) -> dict[str, Any]:
    brand = resolve_brand(params.get("brand"))
    line = normalize_key(params.get("line"))
    version = normalize_key(params.get("version"))
    year = to_int(params.get("year"))
    refs = find_market_references(kind, brand, line, version, year)
    return {"items": refs, "count": len(refs)}
