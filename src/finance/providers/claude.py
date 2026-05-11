from __future__ import annotations

import json
import os
from typing import Iterable

import anthropic

DEFAULT_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
CONFIDENCE_THRESHOLD = float(os.getenv("CLAUDE_CONFIDENCE_THRESHOLD", "0.7"))


class CategorizationError(Exception):
    pass


def _client() -> anthropic.Anthropic:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        raise CategorizationError("ANTHROPIC_API_KEY is not set")
    return anthropic.Anthropic(api_key=key)


_TOOL = {
    "name": "assign_category",
    "description": (
        "Priraď kategóriu k jednej transakcii. Volaj jeden krát pre každú transakciu. "
        "Ak si neistý ktorá kategória sedí, nezavolaj — preskoč."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "entry_reference": {"type": "string", "description": "Identifikátor transakcie"},
            "category_id": {"type": "integer", "description": "ID kategórie zo zoznamu"},
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Istota 0-1 (0.9+ pre jasné prípady, 0.7 pre pravdepodobné)",
            },
        },
        "required": ["entry_reference", "category_id", "confidence"],
    },
}


def _categories_block(categories: Iterable[dict]) -> str:
    lines = []
    for c in categories:
        parent = f" (podkategória: {c['parent_name']})" if c.get("parent_name") else ""
        lines.append(f"- id {c['id']}: {c['name']} [{c['kind']}]{parent}")
    return "\n".join(lines)


def _examples_block(examples: Iterable[dict]) -> str:
    if not examples:
        return "(žiadne historické príklady — používateľ ešte nezaradil žiadne transakcie ručne)"
    lines = []
    for ex in examples:
        cp = ex.get("counterparty_name") or "—"
        info = (ex.get("remittance_info") or "")[:80]
        lines.append(f"- counterparty: \"{cp}\" | info: \"{info}\" → kategória id {ex['category_id']} ({ex['category_name']})")
    return "\n".join(lines)


def _txs_block(txs: Iterable[dict]) -> str:
    lines = []
    for t in txs:
        cp = t.get("counterparty_name") or "—"
        info = (t.get("remittance_info") or "")[:120]
        amt = t.get("amount", "?")
        cur = t.get("currency", "")
        cd = "+" if t.get("credit_debit") == "CRDT" else "−"
        lines.append(
            f"- ref: {t['entry_reference']} | counterparty: \"{cp}\" | info: \"{info}\" "
            f"| {cd}{amt} {cur}"
        )
    return "\n".join(lines)


def categorize_transactions(
    txs: list[dict],
    categories: list[dict],
    examples: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
) -> list[dict]:
    """Calls Claude to categorize a batch of transactions.

    Args:
        txs: rows from db.list_transactions (must contain entry_reference, counterparty_name,
            remittance_info, amount, currency, credit_debit)
        categories: dicts with id, name, kind, parent_name (optional)
        examples: optional historical manually-categorized transactions for few-shot

    Returns:
        list of {"entry_reference": str, "category_id": int, "confidence": float}
        — only items with confidence >= CONFIDENCE_THRESHOLD are returned.
    """
    if not txs:
        return []
    if not categories:
        raise CategorizationError("No categories defined yet")

    system = (
        "Si triediča osobných bankových transakcií zo SK/CZ/EU bánk. "
        "Tvoja úloha: ku každej transakcii priradiť ID kategórie zo zoznamu zavolaním tool-u "
        "`assign_category`.\n\n"
        "Pri analýze hľadaj merchant názov v `counterparty_name` alebo v `info` "
        "(remittance) — často je tam aj keď counterparty je generické 'Transakce platební kartou'.\n\n"
        "## Znalosť bežných obchodov (SK/CZ)\n\n"
        "**Potraviny / supermarkety:**\n"
        "Tesco, Lidl, Kaufland, Albert, Billa, COOP, Jednota, Hruška, Globus, Penny, "
        "Norma, Žabka, EMI POTRAVINY, Tamda, ALBERT VAM DEKUJE, Thi Duyen Nguyen (vietnamské "
        "potraviny), Potraviny Praha, Krajec, Můj obchod, Pramen, La Famiglia.\n\n"
        "**Reštaurácie / fastfood / kaviarne:**\n"
        "McDonald's, KFC, Burger King, Subway, Bageterie Boulevard, Costa Coffee, Starbucks, "
        "Nordsee, Pizza Hut, Ugo, Damejidlo, Wolt, Bolt Food, Foodora, Restaurace, Bistro, Cafe.\n\n"
        "**Doprava:**\n"
        "Bolt, Uber, Liftago, MHD, DPP, IDS, ČD (České dráhy), ZSSK, Leo Express, RegioJet, "
        "FlixBus, Shell, OMV, MOL, Slovnaft, Benzina, Eurowag, Lidl Plus tankovanie, "
        "DHL, GLS, Zásilkovna, ULOŽENKA, Packeta.\n\n"
        "**Bývanie / energie:**\n"
        "ČEZ, E.ON, PRE, innogy, ZSE, SPP, Slovak Telekom, O2, Orange, T-Mobile, Vodafone, "
        "UPC, Magenta, Lyse, ČESKÁ SPOŘITELNA (hypotéka), Komerční banka, Internet, "
        "nájom za mesiac, nájom byt, energie.\n\n"
        "**Subscriptions / online služby:**\n"
        "Netflix, Spotify, HBO, Apple, Google, Microsoft, Amazon, AWS, GitHub, Cloudflare, "
        "Adobe, OpenAI, Anthropic, Notion, Slack, Zoom, ChatGPT, Tinder, Strava, "
        "Steam, PlayStation, Xbox, YouTube Premium, Disney+, Audible.\n\n"
        "**E-shopy / oblečenie / domácnosť:**\n"
        "Alza, Mall.cz, Heureka, Notino, Datart, IKEA, Kik, Pepco, H&M, Zara, "
        "C&A, NewYorker, Dr. Max, Benu, lekáreň, drogerie, Rossmann, dm, Teta, Hornbach, "
        "Bauhaus, OBI, Mountfield, Mountfield, JYSK, XXXLutz, Albo, Sportisimo, Decathlon.\n\n"
        "**Banka / poplatky / prevody:**\n"
        "Poplatok, Bank fee, ČSOB, ATM výber, Cash withdrawal, Trvalý príkaz, Inkaso, "
        "STK, RPSN, úrok, kontokorent.\n\n"
        "**Príjem (CRDT):**\n"
        "Mzda, výplata, plat, Salary, R ALTRA SPOL, BRANISLAV ČIŽMÁR (vlastný presun), "
        "Vrátená platba, refund, cashback, dividenda, úrok pripísaný.\n\n"
        "## Pravidlá\n"
        "- Hľadaj substring match na merchant názvy hore (napr. 'ALBERT VAM DEKUJE' → "
        "  Albert → potraviny). Veľké/malé písmená nehrajú rolu.\n"
        "- Ak vidíš jasný merchant z bežného zoznamu → confidence 0.85-0.95.\n"
        "- Ak je len generický popis ('Transakce platební kartou' bez čehokoľvek iného) → "
        "  preskoč, neraď.\n"
        "- Pri záporných sumách = výdaj (DBIT), pri kladných = príjem (CRDT). "
        "  Mapuj na kategóriu správneho `kind`.\n"
        "- Pri presunoch medzi vlastnými účtami (counterparty má rovnaké priezvisko ako majiteľ, "
        "  alebo je to 'BRANISLAV ČIŽMÁR' atď.) použi kategóriu typu 'transfer' (napr. Sporenie).\n"
        "- **Historické príklady používateľa majú prioritu** nad mojou všeobecnou znalosťou. "
        "  Ak používateľ podobnú transakciu zaradil inde, urob to tak isto.\n"
        "- Confidence: 0.9+ pre jasné prípady, 0.7-0.9 pre rozumné dohad, pod 0.7 PRESKOČ.\n"
    )

    user = (
        f"## Kategórie\n{_categories_block(categories)}\n\n"
        f"## Historické príklady (čo používateľ ručne zaradil v minulosti)\n"
        f"{_examples_block(examples or [])}\n\n"
        f"## Transakcie na zaradenie\n{_txs_block(txs)}\n\n"
        "Pre každú transakciu zavolaj `assign_category` (alebo preskoč ak si neistý)."
    )

    client = _client()
    resp = client.messages.create(
        model=model,
        max_tokens=4096,
        system=[
            {"type": "text", "text": system},
        ],
        tools=[_TOOL],
        messages=[{"role": "user", "content": user}],
    )

    results: list[dict] = []
    for block in resp.content:
        if block.type == "tool_use" and block.name == "assign_category":
            inp = block.input
            try:
                conf = float(inp.get("confidence", 0))
                if conf < CONFIDENCE_THRESHOLD:
                    continue
                results.append({
                    "entry_reference": str(inp["entry_reference"]),
                    "category_id": int(inp["category_id"]),
                    "confidence": conf,
                })
            except (KeyError, TypeError, ValueError):
                continue
    return results
