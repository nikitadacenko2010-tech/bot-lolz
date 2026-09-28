from __future__ import annotations

import asyncio
import html
import json
import logging
import os
from pathlib import Path
import secrets
import sys
import time

import httpx


from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("playerok_deals_bot")

def _get_token() -> str:
    token = (os.getenv("BOT_TOKEN") or "8842922871:AAEVe_8phJnV84ssHelPuY1h_h0QeXCyheY").strip()
    if token:
        return token
    if len(sys.argv) >= 2 and sys.argv[1].strip():
        return sys.argv[1].strip()
    return ""


def _get_lang(user_id: int) -> str:
    langs = _load_json(LANGS_PATH)
    v = langs.get(str(user_id))
    return v if v in ("ru", "en") else "ru"


def _set_lang(user_id: int, lang: str) -> None:
    langs = _load_json(LANGS_PATH)
    langs[str(user_id)] = lang
    _save_json(LANGS_PATH, langs)


def tr(user_id: int, key: str, **kw: object) -> str:
    lang = _get_lang(user_id)
    RU = {
        "back": "Назад",
        "to_menu": "В меню",
        "cancel": "Отмена",
        "saved": "✅ Сохранено",
        "join_deal": "Присоединиться к сделке",
        "i_paid": "Подтвердить получение",
        "i_delivered": "Я передал менеджеру",
        "i_received": "Получил товар (завершить)",
        "cancel_deal": "Отменить сделку",
        "deal": "Сделка",
        "status": "Статус",
        "you": "Вы",
        "buyer": "Покупатель",
        "seller": "Продавец",
        "currency": "Валюта",
        "amount": "Сумма",
        "desc": "Описание",
        "share_link": "Ссылка для второго участника",
        "status_created": "ожидает второго участника",
        "status_joined": "участники собраны",
        "status_paid": "оплачено покупателем",
        "status_delivered": "продавец передал товар",
        "status_completed": "завершена",
        "status_cancelled": "отменена",
        "menu_reqs": "Мои реквизиты",
        "menu_create": "Создать сделку",
        "menu_balance": "Баланс",
        "menu_my_deals": "Мои сделки",
        "menu_ref": "Рефералы",
        "menu_lang": "Язык / Lang",
        "menu_support": "Техподдержка",
        "support_url": "https://t.me/playerokspr",
        "ref_title": "Реферальная программа",
        "ref_link": "Ваша ссылка",
        "ref_count": "Рефералов",
        "ref_earned": "Заработано",
        "ref_bonus": "Бонус: 50% от комиссии с каждой сделки реферала!",
        "lang_title": "Язык / Lang",
        "lang_current": "Текущий язык",
        "lang_choose": "Выберите язык кнопкой ниже",
        "lang_ru": "Русский",
        "lang_en": "English",
        "mydeals_title": "Мои сделки",
        "mydeals_total": "Всего",
        "mydeals_completed": "Завершено",
        "deal_open": "Сделка #{id}",
        "payment_received": "Оплата получена",
        "payment_received_desc": "Покупатель подтвердил оплату. Ожидайте передачи товара от продавца.",
    }
    EN = {
        "back": "Back",
        "to_menu": "Menu",
        "cancel": "Cancel",
        "saved": "✅ Saved",
        "join_deal": "Join deal",
        "i_paid": "Confirm receipt",
        "i_delivered": "I delivered item",
        "i_received": "Received (complete)",
        "cancel_deal": "Cancel deal",
        "deal": "Deal",
        "status": "Status",
        "you": "You",
        "buyer": "Buyer",
        "seller": "Seller",
        "currency": "Currency",
        "amount": "Amount",
        "desc": "Description",
        "share_link": "Link for the other party",
        "status_created": "waiting for the second party",
        "status_joined": "both parties joined",
        "status_paid": "paid by buyer",
        "status_delivered": "item delivered by seller",
        "status_completed": "completed",
        "status_cancelled": "cancelled",
        "menu_reqs": "My payment details",
        "menu_create": "Create deal",
        "menu_balance": "Balance",
        "menu_my_deals": "My deals",
        "menu_ref": "Referrals",
        "menu_lang": "Language",
        "menu_support": "Support",
        "support_url": "https://t.me/dukeVercase",
        "ref_title": "Referral program",
        "ref_link": "Your link",
        "ref_count": "Referrals",
        "ref_earned": "Earned",
        "ref_bonus": "Bonus: 50% of the fee from each referral deal!",
        "lang_title": "Language",
        "lang_current": "Current language",
        "lang_choose": "Choose a language below",
        "lang_ru": "Русский",
        "lang_en": "English",
        "mydeals_title": "My deals",
        "mydeals_total": "Total",
        "mydeals_completed": "Completed",
        "deal_open": "Deal #{id}",
        "payment_received": "Payment received",
        "payment_received_desc": "Buyer confirmed payment. Waiting for seller to deliver the item.",
    }
    table = EN if lang == "en" else RU
    s = table.get(key, key)
    try:
        return str(s).format(**kw)
    except Exception:
        return str(s)

ROOT = Path(__file__).resolve().parent
WELCOME_PHOTO_PATH = ROOT / "forbot.jpg"
DATA_PATH = ROOT / "reqs.json"
DEALS_PATH = ROOT / "deals.json"
BALANCES_PATH = ROOT / "balances.json"
REFS_PATH = ROOT / "refs.json"
LANGS_PATH = ROOT / "langs.json"
BANS_PATH = ROOT / "bans.json"
COMPLETED_DEALS_BOOST_PATH = ROOT / "completed_deals_boost.json"

# Premium-эмодзи (document_id) для HTML: <tg-emoji emoji-id='…'>символ</tg-emoji>
E: dict[str, str] = {
    "💼": "5893255507380014983",
    "🤝": "5395732581780040886",
    "⚡️": "5456140674028019486",
    "1⃣": "5794164805065514131",
    "2⃣": "5794085322400733645",
    "🛡": "5902016123972358349",
    "3⃣": "5794280000383358988",
    "🪙": "6039802097916974085",
    "4⃣": "5794241397217304511",
    "📦": "5778672437122045013",
    "💡": "5893290369629556374",
    "⬇️": "5406745015365943482",
    "🏖": "5199790590279033017",
    "🧑‍🎓": "5206186681346039457",
    "💪": "5228804314134226293",
    "😎": "5388929052935462187",
    "😘": "5409351484988987888",
    "🫥": "5246885387716011812",
    "😇": "5226876951855113572",
    "📌": "5895440460322706085",
    "💎": "5427168083074628963",
    "💳": "5445353829304387411",
    "⭐️": "5924870095925942277",
    "🚽": "5195227797412387977",
    "📞": "5226772700113935347",
    "💭": "5467538555158943525",
    "👑": "5217822164362739968",
    "🛒": "5312361253610475399",
    "❗️": "5274099962655816924",
    "🏦": "5332455502917949981",
    "💸": "5231449120635370684",
    "💳_CUR": "5269292098955256141",
    "🫰": "5210744041079063997",
    "💵": "5427298452511947188",
    "💰": "5893473283696759404",
    "✍️": "5197269100878907942",
    "✅": "5895713431264170680",
    "🔗": "5902449142575141204",
    "🇷🇺": "5449408995691341691",
    "🧩": "5213306719215577669",
    "💔": "5316583309541651465",
    "📈": "5244837092042750681",
    "👥": "6032609071373226027",
    "📊_DEALS": "5190806721286657692",
    "✅_DEALS": "5902002809573740949",
    "🚫": "5278578973595427038",
    "💱": "5377336227533969892",
    "👛": "5215420556089776398",
    "🎉": "5940229376336519160",  # добавлено для уведомления об оплате
    "🟢": "5331090125612144385",   # добавлено для статуса
}

# Иконки для InlineKeyboardButton.icon_custom_emoji_id
ICON: dict[str, str] = dict(E)
ICON["🪙_USDT"] = "6039802097916974085"
ICON["🪙_BTC"] = "5816788957614053645"
ICON["💸_RUB"] = E["💸"]
ICON["💳_UAH"] = E["💳_CUR"]
ICON["🫰_KZT"] = E["🫰"]
ICON["💵_BYN"] = E["💵"]
ICON["📊_DEALS"] = E["📊_DEALS"]
ICON["✅_DEALS"] = E["✅_DEALS"]

ADMIN_IDS = frozenset({8281274109})


def _load_json(path: Path) -> dict:
    try:
        if not path.exists():
            return {}
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_json(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _get_crypto_pay_token() -> str:
    return (os.getenv("CRYPTO_PAY_TOKEN") or "563838:AA7lGNSwnu5KniyqyAKgoBvb5CURSXPR2zx").strip()


async def cryptopay_get_exchange_rates(token: str) -> list[dict]:
    headers = {"Crypto-Pay-API-Token": token}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://pay.crypt.bot/api/getExchangeRates", json={}, headers=headers)
        data = r.json()
        if not data.get("ok"):
            return []
        result = data.get("result")
        if isinstance(result, list):
            return [x for x in result if isinstance(x, dict)]
        if isinstance(result, dict):
            rates = result.get("items") or result.get("rates") or result.get("data") or []
            return rates if isinstance(rates, list) else []
        return []


async def _fallback_rub_to_target_rate(target: str) -> float | None:
    target = str(target).upper()
    if target == "RUB":
        return 1.0
    if target == "STARS":
        return 1.0

    if target in {"UAH", "KZT", "BYN"}:
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                r = await client.get("https://open.er-api.com/v6/latest/RUB")
                data = r.json()
                rates = data.get("rates") if isinstance(data, dict) else None
                if isinstance(rates, dict):
                    raw = rates.get(target)
                    val = float(raw) if raw is not None else 0.0
                    if val > 0:
                        return val
        except Exception:
            pass
        return None

    coin_map = {"USDT": "tether", "BTC": "bitcoin"}
    coin_id = coin_map.get(target)
    if not coin_id:
        return None
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "rub"},
            )
            data = r.json()
            rub_per_coin = float((data.get(coin_id) or {}).get("rub") or 0.0)
            if rub_per_coin > 0:
                return 1.0 / rub_per_coin
    except Exception:
        pass
    return None


async def rub_to_currency_rate(context: ContextTypes.DEFAULT_TYPE, target: str) -> float | None:
    target = str(target).upper()
    if target in {"RUB", "STARS"}:
        return 1.0

    token = _get_crypto_pay_token()
    if token:
        rates = await cryptopay_get_exchange_rates(token)
        for it in rates:
            if not isinstance(it, dict):
                continue
            src = str(it.get("source") or it.get("from") or "").upper()
            dst = str(it.get("target") or it.get("to") or "").upper()
            if src == "RUB" and dst == target:
                try:
                    rate = float(it.get("rate"))
                except Exception:
                    rate = 0.0
                if rate > 0:
                    return rate

    return await _fallback_rub_to_target_rate(target)


async def rub_needed_for_currency(context: ContextTypes.DEFAULT_TYPE, target: str, amount_target: float) -> float | None:
    if amount_target <= 0:
        return None
    target = str(target).upper()
    if target == "STARS":
        return float(amount_target)
    rate = await rub_to_currency_rate(context, target)
    if rate is None or rate <= 0:
        return None
    return float(amount_target) / rate


async def convert_currency_amount(
    context: ContextTypes.DEFAULT_TYPE,
    amount: float,
    from_cur: str,
    to_cur: str,
) -> tuple[float, float] | None:
    from_cur = str(from_cur).upper()
    to_cur = str(to_cur).upper()
    if amount <= 0:
        return None
    if from_cur == to_cur:
        return None

    if from_cur in {"RUB", "STARS"}:
        rub_amount = float(amount)
    else:
        from_rate = await rub_to_currency_rate(context, from_cur)
        if from_rate is None or from_rate <= 0:
            return None
        rub_amount = float(amount) / from_rate

    if to_cur in {"RUB", "STARS"}:
        out_amount = rub_amount
    else:
        to_rate = await rub_to_currency_rate(context, to_cur)
        if to_rate is None or to_rate <= 0:
            return None
        out_amount = rub_amount * to_rate

    return rub_amount, out_amount


async def cryptopay_create_invoice(token: str, user_id: int, rub_amount: float) -> dict | None:
    headers = {"Crypto-Pay-API-Token": token}
    payload = {
        "amount": f"{rub_amount:.2f}",
        "currency_type": "fiat",
        "fiat": "RUB",
        "description": f"Playerok Deals deposit #{user_id}",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://pay.crypt.bot/api/createInvoice", json=payload, headers=headers)
        data = r.json()
        if not data.get("ok"):
            return None
        return data.get("result")


async def cryptopay_get_invoice(token: str, invoice_id: int) -> dict | None:
    headers = {"Crypto-Pay-API-Token": token}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(
            "https://pay.crypt.bot/api/getInvoices",
            json={"invoice_ids": [invoice_id]},
            headers=headers,
        )
        data = r.json()
        if not data.get("ok"):
            return None
        items = (data.get("result") or {}).get("items") or []
        if not items:
            return None
        return items[0]


def kb_deposit_methods() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="CryptoBot",
                    callback_data="dep_cryptobot",
                    icon_custom_emoji_id=ICON["👛"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="balance",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ],
        ]
    )


def kb_invoice(pay_url: str, invoice_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить счёт",
                    url=pay_url,
                    icon_custom_emoji_id=ICON["💱"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Проверить оплату",
                    callback_data=f"dep_check_{invoice_id}",
                    icon_custom_emoji_id=ICON["✅"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="balance",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ],
        ]
    )


async def on_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        (
            f"<b>{pe('👛')} Пополнение</b>\n\n"
            f"<blockquote><b>{pe('💭')} Выберите способ пополнения</b></blockquote>\n\n"
            f"<b>{pe('💡')} После оплаты баланс обновится автоматически</b>"
        ),
        reply_markup=kb_deposit_methods(),
    )


async def on_dep_cryptobot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    if not _get_crypto_pay_token():
        await q.message.reply_html(f"<b>{pe('❗️')} Нет CRYPTO_PAY_TOKEN в окружении</b>")
        return
    context.user_data["dep_await"] = "rub"
    context.user_data["dep_panel"] = {"chat_id": q.message.chat_id, "message_id": q.message.message_id}
    await q.message.reply_html(
        f"<b>{pe('💰')} Введите сумму пополнения в рублях:</b>\n\n"
        f"<blockquote><b>{pe('💡')} Пример:</b> <code>1000</code> или <code>1499.50</code></blockquote>",
        reply_markup=kb_one_back("deposit_cancel"),
    )


async def on_deposit_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    context.user_data.pop("dep_await", None)
    try:
        await q.message.delete()
    except Exception:
        pass


async def _auto_check_invoice(app: Application, user_id: int, invoice_id: int, rub_amount: float) -> None:
    token = _get_crypto_pay_token()
    if not token:
        return
    for _ in range(90):
        await asyncio.sleep(5)
        inv = await cryptopay_get_invoice(token, invoice_id)
        if not inv:
            continue
        if str(inv.get("status")) == "paid":
            _add_balance(user_id, "RUB", rub_amount)
            try:
                await app.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"<b>{pe('✅')} Пополнение успешно</b>\n\n"
                        f"<blockquote><b>{pe('💰')} +{rub_amount:.2f} RUB</b></blockquote>\n\n"
                        f"<b>{pe('💡')} Баланс обновлён</b>"
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
            return


async def on_dep_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    token = _get_crypto_pay_token()
    if not token:
        await q.answer("Нет CRYPTO_PAY_TOKEN", show_alert=True)
        return
    invoice_id = int((q.data or "").replace("dep_check_", "", 1))
    pending = context.application.bot_data.get("pending_dep") or {}
    if not isinstance(pending, dict) or str(invoice_id) not in pending:
        await q.answer("Счёт не найден", show_alert=True)
        return
    rub_amount = float(pending[str(invoice_id)]["rub_amount"])
    inv = await cryptopay_get_invoice(token, invoice_id)
    if not inv:
        await q.answer("Ошибка проверки", show_alert=True)
        return
    if str(inv.get("status")) == "paid":
        if not pending[str(invoice_id)].get("_credited"):
            pending[str(invoice_id)]["_credited"] = True
            _add_balance(q.from_user.id, "RUB", rub_amount)
        await q.message.reply_html(
            f"<b>{pe('✅')} Оплачено</b>\n\n<blockquote><b>{pe('💰')} +{rub_amount:.2f} RUB</b></blockquote>",
        )
        return
    await q.answer("Оплата не найдена. Попробуйте ещё раз через пару секунд.", show_alert=True)


async def on_deposit_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    if context.user_data.get("dep_await") != "rub":
        return
    raw = msg.text.strip().replace(",", ".").replace(" ", "")
    try:
        rub_amount = float(raw)
    except Exception:
        await msg.reply_html(f"<b>{pe('❗️')} Введите число</b>")
        return
    if rub_amount <= 0:
        await msg.reply_html(f"<b>{pe('❗️')} Сумма должна быть больше 0</b>")
        return

    token = _get_crypto_pay_token()
    if not token:
        await msg.reply_html(f"<b>{pe('❗️')} Нет CRYPTO_PAY_TOKEN</b>")
        return

    inv = await cryptopay_create_invoice(token, user.id, rub_amount)
    if not inv:
        await msg.reply_html(f"<b>{pe('❗️')} Не удалось создать счёт</b>")
        return

    invoice_id = int(inv.get("invoice_id"))
    pay_url = inv.get("pay_url") or inv.get("bot_invoice_url") or inv.get("mini_app_invoice_url")
    if not pay_url:
        await msg.reply_html(f"<b>{pe('❗️')} Нет ссылки на оплату</b>")
        return

    context.user_data.pop("dep_await", None)
    pending = context.application.bot_data.get("pending_dep")
    if not isinstance(pending, dict):
        pending = {}
        context.application.bot_data["pending_dep"] = pending
    pending[str(invoice_id)] = {"user_id": user.id, "rub_amount": rub_amount, "_credited": False}

    try:
        asyncio.create_task(_auto_check_invoice(context.application, user.id, invoice_id, rub_amount))
    except Exception:
        pass

    await msg.reply_html(
        f"<b>{pe('👛')} Счёт на {rub_amount:.2f} RUB</b>\n\n"
        f"<blockquote><b>{pe('💡')} Оплатите любым способом (USDT/TON/…)</b></blockquote>\n\n"
        f"<b>{pe('📢')} После оплаты нажмите «Проверить оплату»</b>",
        reply_markup=kb_invoice(pay_url, invoice_id),
        disable_web_page_preview=True,
    )


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def is_banned(user_id: int) -> bool:
    bans = _load_json(BANS_PATH)
    return bool(bans.get(str(user_id)))


def ban_user(user_id: int) -> None:
    bans = _load_json(BANS_PATH)
    bans[str(user_id)] = True
    _save_json(BANS_PATH, bans)


def unban_user(user_id: int) -> None:
    bans = _load_json(BANS_PATH)
    bans.pop(str(user_id), None)
    _save_json(BANS_PATH, bans)


async def access_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    if is_admin(user.id):
        return
    if is_banned(user.id):
        if update.callback_query:
            try:
                await update.callback_query.answer("Доступ запрещён", show_alert=True)
            except Exception:
                pass
        if update.effective_message:
            await update.effective_message.reply_html(f"<b>{pe('❗️')} Доступ запрещён</b>")
        return


def pe(symbol: str) -> str:
    eid = E.get(symbol)
    if not eid:
        return html.escape(symbol)
    return f"<tg-emoji emoji-id='{eid}'>{html.escape(symbol)}</tg-emoji>"

def pe_id(symbol: str, emoji_id: str) -> str:
    return f"<tg-emoji emoji-id='{emoji_id}'>{html.escape(symbol)}</tg-emoji>"


def _load_reqs() -> dict[str, dict[str, str]]:
    try:
        if not DATA_PATH.exists():
            return {}
        raw = DATA_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_reqs(data: dict[str, dict[str, str]]) -> None:
    tmp = DATA_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DATA_PATH)

def _load_deals() -> dict[str, dict]:
    try:
        if not DEALS_PATH.exists():
            return {}
        raw = DEALS_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_deals(data: dict[str, dict]) -> None:
    tmp = DEALS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DEALS_PATH)

def _load_balances() -> dict[str, dict[str, float]]:
    try:
        if not BALANCES_PATH.exists():
            return {}
        raw = BALANCES_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_balances(data: dict[str, dict[str, float]]) -> None:
    tmp = BALANCES_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(BALANCES_PATH)


def _get_balance(user_id: int) -> dict[str, float]:
    data = _load_balances()
    u = data.get(str(user_id))
    if isinstance(u, dict):
        out: dict[str, float] = {}
        for k, v in u.items():
            try:
                out[str(k)] = float(v)
            except Exception:
                out[str(k)] = 0.0
        return out
    return {}


def _add_balance(user_id: int, currency: str, amount: float) -> None:
    if amount <= 0:
        return
    data = _load_balances()
    u = data.get(str(user_id))
    if not isinstance(u, dict):
        u = {}
        data[str(user_id)] = u
    cur = str(currency)
    prev = float(u.get(cur) or 0.0)
    u[cur] = prev + float(amount)
    _save_balances(data)


def _deduct_balance(user_id: int, currency: str, amount: float) -> bool:
    if amount <= 0:
        return False
    data = _load_balances()
    u = data.get(str(user_id))
    if not isinstance(u, dict):
        return False
    cur = str(currency)
    prev = float(u.get(cur) or 0.0)
    if prev + 1e-9 < float(amount):
        return False
    u[cur] = max(0.0, prev - float(amount))
    data[str(user_id)] = u
    _save_balances(data)
    return True


def _count_completed_deals(user_id: int) -> int:
    boosted_raw = _load_json(COMPLETED_DEALS_BOOST_PATH).get(str(user_id))
    if boosted_raw is not None:
        try:
            boosted = int(float(boosted_raw))
            if boosted >= 0:
                return boosted
        except Exception:
            pass
    deals = _load_deals()
    n = 0
    for d in deals.values():
        if not isinstance(d, dict):
            continue
        if str(d.get("status")) != "completed":
            continue
        if d.get("buyer_id") == user_id or d.get("seller_id") == user_id:
            n += 1
    return n


def _set_completed_deals_boost(user_id: int, total_completed: int) -> None:
    data = _load_json(COMPLETED_DEALS_BOOST_PATH)
    data[str(user_id)] = max(0, int(total_completed))
    _save_json(COMPLETED_DEALS_BOOST_PATH, data)


def balance_caption_html(user_id: int) -> str:
    bal = _get_balance(user_id)
    completed = _count_completed_deals(user_id)
    if not bal or all((v or 0.0) <= 0 for v in bal.values()):
        bal_line = f"<b>{pe('💔')} Ваш баланс пока пуст</b>"
    else:
        parts = []
        for cur, amt in sorted(bal.items()):
            if amt and amt > 0:
                parts.append(f"<b>{html.escape(cur)}:</b> <code>{amt:.6f}</code>" if cur in ("USDT", "BTC") else f"<b>{html.escape(cur)}:</b> <code>{amt:.2f}</code>")
        bal_line = "<b>Баланс:</b>\n" + "\n".join(parts) if parts else f"<b>{pe('💔')} Ваш баланс пока пуст</b>"
    return (
        f"<b>{pe('💰')} Ваш баланс:</b>\n\n"
        f"{bal_line}\n\n"
        f"<b>{pe('📈')} Завершённых сделок:</b> <code>{completed}</code>\n\n"
        f"<b>{pe('❗️')} Для вывода средств необходимо минимум 1 завершённых сделок</b>"
    )


def kb_balance() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Пополнить",
                    callback_data="deposit",
                    icon_custom_emoji_id=ICON["💱"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Обмен валют",
                    callback_data="exchange",
                    icon_custom_emoji_id=ICON["💱"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Вывод средств",
                    callback_data="withdraw",
                    icon_custom_emoji_id=ICON["💰"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="bal_back",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ],
        ]
    )


def kb_withdraw_currency() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("RUB", callback_data="wd_cur_RUB", icon_custom_emoji_id=ICON["💸_RUB"]),
                InlineKeyboardButton("UAH", callback_data="wd_cur_UAH", icon_custom_emoji_id=ICON["💳_UAH"]),
            ],
            [
                InlineKeyboardButton("KZT", callback_data="wd_cur_KZT", icon_custom_emoji_id=ICON["🫰_KZT"]),
                InlineKeyboardButton("BYN", callback_data="wd_cur_BYN", icon_custom_emoji_id=ICON["💵_BYN"]),
            ],
            [
                InlineKeyboardButton("STARS", callback_data="wd_cur_STARS", icon_custom_emoji_id=ICON["⭐️"]),
            ],
            [
                InlineKeyboardButton("USDT", callback_data="wd_cur_USDT", icon_custom_emoji_id=ICON["🪙_USDT"]),
                InlineKeyboardButton("BTC", callback_data="wd_cur_BTC", icon_custom_emoji_id=ICON["🪙_BTC"]),
            ],
            [
                InlineKeyboardButton("Назад", callback_data="withdraw_back", icon_custom_emoji_id=ICON["🚽"]),
            ],
        ]
    )


async def on_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        balance_caption_html(q.from_user.id),
        reply_markup=kb_balance(),
    )


async def on_bal_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        welcome_caption_html(q.from_user.id),
        reply_markup=kb_welcome(q.from_user.id),
    )


async def on_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    if _count_completed_deals(q.from_user.id) < 1:
        await _edit_query_message(
            q,
            balance_caption_html(q.from_user.id),
            reply_markup=kb_balance(),
        )
        return
    context.user_data["wd"] = {}
    await _edit_query_message(
        q,
        f"<b>{pe('💱')} Вывод средств</b>\n\n<blockquote><b>{pe('🏦')} Выберите валюту вывода</b></blockquote>",
        reply_markup=kb_withdraw_currency(),
    )


async def on_withdraw_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        balance_caption_html(q.from_user.id),
        reply_markup=kb_balance(),
    )


async def on_wd_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    cur = (q.data or "").replace("wd_cur_", "", 1)
    if cur not in ("RUB", "UAH", "KZT", "BYN", "STARS", "USDT", "BTC"):
        return
    context.user_data["wd"] = {"currency": cur}
    context.user_data["wd_await"] = "amount"
    await q.message.reply_html(
        f"<b>{pe('💰')} Введите сумму для вывода ({html.escape(cur)}):</b>",
        reply_markup=kb_one_back("withdraw_back"),
    )


async def on_withdraw_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    if context.user_data.get("wd_await") != "amount":
        return
    wd = context.user_data.get("wd")
    if not isinstance(wd, dict) or not wd.get("currency"):
        return
    cur = str(wd["currency"])
    raw = msg.text.strip().replace(",", ".")
    try:
        amt = float(raw)
    except ValueError:
        await msg.reply_html(f"<b>{pe('❗️')} Введите число</b>")
        return
    if amt <= 0:
        await msg.reply_html(f"<b>{pe('❗️')} Сумма должна быть больше 0</b>")
        return
    bal = _get_balance(user.id).get(cur, 0.0)
    if bal + 1e-9 < amt:
        await msg.reply_html(
            f"<b>{pe('❗️')} Недостаточно средств</b>\n\n"
            f"<blockquote><b>Доступно:</b> <code>{bal}</code> {html.escape(cur)}</blockquote>",
        )
        return
    _deduct_balance(user.id, cur, amt)
    context.user_data.pop("wd_await", None)
    await msg.reply_html(
        f"<b>{pe('✅')} Ожидайте вывода…</b>\n\n"
        f"<blockquote><b>{pe('💰')} Сумма:</b> <code>{amt}</code> {html.escape(cur)}</blockquote>",
    )

def _new_deal_id() -> str:
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


async def _get_bot_username(context: ContextTypes.DEFAULT_TYPE) -> str:
    cached = context.application.bot_data.get("bot_username")
    if isinstance(cached, str) and cached:
        return cached
    me = await context.bot.get_me()
    uname = (me.username or "").strip()
    if uname:
        context.application.bot_data["bot_username"] = uname
        return uname
    return "playerokbot"


def _deal_link(username: str, deal_id: str) -> str:
    return f"https://t.me/{username}?start=deal_{deal_id}"


def kb_one_back(callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=callback_data,
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        ]
    )

def _ex_offer_store_app(context: ContextTypes.DEFAULT_TYPE) -> dict:
    st = context.application.bot_data.get("ex_offers")
    if not isinstance(st, dict):
        st = {}
        context.application.bot_data["ex_offers"] = st
    return st


def kb_exchange_offer(token: str, back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Обмен валют",
                    callback_data=f"ex_offer_{token}",
                    icon_custom_emoji_id=ICON["💱"],
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=back_cb,
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ],
        ]
    )


def warn_no_card_caption_html() -> str:
    return f"<b>{pe('❗️')} Сначала добавьте данные карты в «Мои реквизиты».</b>"

def warn_no_stars_caption_html() -> str:
    return f"<b>{pe('❗️')} Сначала добавьте Stars в «Мои реквизиты».</b>"


def warn_no_crypto_caption_html() -> str:
    return f"<b>{pe('❗️')} Сначала добавьте USDT (TRC20) или BTC в «Мои реквизиты».</b>"


def _get_user_reqs(user_id: int) -> dict[str, str]:
    data = _load_reqs()
    u = data.get(str(user_id))
    if isinstance(u, dict):
        return {k: str(v) for k, v in u.items()}
    return {}


def _set_user_req(user_id: int, key: str, value: str) -> None:
    data = _load_reqs()
    u = data.get(str(user_id))
    if not isinstance(u, dict):
        u = {}
        data[str(user_id)] = u
    u[key] = value
    _save_reqs(data)


def reqs_caption_html(user_id: int) -> str:
    r = _get_user_reqs(user_id)
    ton = html.escape(r.get("ton", "—") or "—")
    card = html.escape(r.get("card", "—") or "—")
    stars = html.escape(r.get("stars", "—") or "—")
    usdt = html.escape(r.get("usdt", "—") or "—")
    btc = html.escape(r.get("btc", "—") or "—")
    return (
        f"<b>{pe('📌')} Мои реквизиты</b>\n\n"
        f"<blockquote>"
        f"<b>{pe('💎')} TON-кошелёк:</b> {ton}\n"
        f"<b>{pe('💳')} Карта:</b> {card}\n"
        f"<b>{pe('⭐️')} Stars:</b> {stars}\n"
        f"<b>{pe_id('🪙', '6039802097916974085')} USDT (TRC20):</b> {usdt}\n"
        f"<b>{pe_id('🪙', '5816788957614053645')} BTC:</b> {btc}"
        f"</blockquote>"
    )


def kb_reqs() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="TON-кошелёк",
                    callback_data="req_edit_ton",
                    icon_custom_emoji_id=ICON["💎"],
                ),
                InlineKeyboardButton(
                    text="Карта",
                    callback_data="req_edit_card",
                    icon_custom_emoji_id=ICON["💳"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Stars",
                    callback_data="req_edit_stars",
                    icon_custom_emoji_id=ICON["⭐️"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="USDT (TRC20)",
                    callback_data="req_edit_usdt",
                    icon_custom_emoji_id=ICON["🪙_USDT"],
                ),
                InlineKeyboardButton(
                    text="BTC",
                    callback_data="req_edit_btc",
                    icon_custom_emoji_id=ICON["🪙_BTC"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="req_back",
                    icon_custom_emoji_id=ICON["🚽"],
                ),
            ],
        ]
    )

def kb_cancel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data="req_cancel",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        ]
    )


def kb_saved() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад в профиль",
                    callback_data="req_go_profile",
                    icon_custom_emoji_id=ICON["📞"],
                )
            ]
        ]
    )


async def _edit_to_reqs_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.message or not q.from_user:
        return
    context.user_data["reqs_panel"] = {"chat_id": q.message.chat_id, "message_id": q.message.message_id}
    await _edit_query_message(
        q,
        reqs_caption_html(q.from_user.id),
        reply_markup=kb_reqs(),
    )


async def on_my_reqs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    await _edit_to_reqs_panel(update, context)


async def on_req_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    context.user_data.pop("awaiting_req", None)
    await _edit_query_message(
        q,
        welcome_caption_html(q.from_user.id),
        reply_markup=kb_welcome(q.from_user.id),
    )


def _awaiting_prompt(symbol: str, label: str) -> str:
    return f"<b>{pe(symbol)} Введите {label}:</b>"


async def _begin_awaiting(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str, prompt_html: str) -> None:
    q = update.callback_query
    if not q or not q.message:
        return
    await q.answer()
    context.user_data["awaiting_req"] = key
    context.user_data["reqs_panel"] = {"chat_id": q.message.chat_id, "message_id": q.message.message_id}
    await q.message.reply_html(prompt_html, reply_markup=kb_cancel())


async def on_req_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer("Отменено")
    context.user_data.pop("awaiting_req", None)
    try:
        await q.message.delete()
    except Exception:
        pass


async def on_req_go_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    panel = context.user_data.get("reqs_panel") or {}
    chat_id = panel.get("chat_id")
    message_id = panel.get("message_id")
    if chat_id and message_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=reqs_caption_html(q.from_user.id),
                parse_mode=ParseMode.HTML,
                reply_markup=kb_reqs(),
            )
        except Exception:
            pass
    try:
        await q.message.delete()
    except Exception:
        pass


async def on_req_edit_ton(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _begin_awaiting(update, context, "ton", _awaiting_prompt("💎", "TON-кошелёк"))


async def on_req_edit_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _begin_awaiting(update, context, "card", _awaiting_prompt("💳", "номер карты"))


async def on_req_edit_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _begin_awaiting(
        update,
        context,
        "stars",
        f"<b>{pe('⭐️')} Введите Stars (юзернейм кому приходят звезды):</b>",
    )


async def on_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("awaiting_req"):
        await on_reqs_text(update, context)
        return
    if context.user_data.get("mamont_await"):
        await on_mamont_amount_text(update, context)
        return
    if context.user_data.get("dep_await"):
        await on_deposit_text(update, context)
        return
    if context.user_data.get("ex_await"):
        await on_exchange_text(update, context)
        return
    if context.user_data.get("wd_await"):
        await on_withdraw_text(update, context)
        return
    if context.user_data.get("deal_await"):
        await on_deal_text(update, context)
        return


def kb_mamont_currencies() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton("RUB", callback_data="mam_cur_RUB", icon_custom_emoji_id=ICON["💸_RUB"]),
                InlineKeyboardButton("UAH", callback_data="mam_cur_UAH", icon_custom_emoji_id=ICON["💳_UAH"]),
            ],
            [
                InlineKeyboardButton("KZT", callback_data="mam_cur_KZT", icon_custom_emoji_id=ICON["🫰_KZT"]),
                InlineKeyboardButton("BYN", callback_data="mam_cur_BYN", icon_custom_emoji_id=ICON["💵_BYN"]),
            ],
            [
                InlineKeyboardButton("STARS", callback_data="mam_cur_STARS", icon_custom_emoji_id=ICON["⭐️"]),
            ],
            [
                InlineKeyboardButton("USDT", callback_data="mam_cur_USDT", icon_custom_emoji_id=ICON["🪙_USDT"]),
                InlineKeyboardButton("BTC", callback_data="mam_cur_BTC", icon_custom_emoji_id=ICON["🪙_BTC"]),
            ],
            [
                InlineKeyboardButton("Накрутить сделки", callback_data="mam_boost_deals", icon_custom_emoji_id=ICON["📈"]),
            ],
            [
                InlineKeyboardButton("Назад", callback_data="mam_back", icon_custom_emoji_id=ICON["🚽"]),
            ],
        ]
    )


async def cmd_mamontsosi(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return
    await update.effective_message.reply_html(
        f"<b>{pe('💰')} Выдать баланс</b>\n\n"
        f"<blockquote><b>{pe('💭')} Выберите валюту</b></blockquote>",
        reply_markup=kb_mamont_currencies(),
    )


EXCHANGE_CURRENCIES = ("RUB", "UAH", "KZT", "BYN", "STARS", "USDT", "BTC")


def _ex_btn_label(cur: str, selected: bool) -> str:
    return f"✅ {cur}" if selected else cur


def kb_exchange_pick_from(selected: str | None = None) -> InlineKeyboardMarkup:
    selected = (selected or "").upper()
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(_ex_btn_label("RUB", selected == "RUB"), callback_data="ex_from_RUB", icon_custom_emoji_id=ICON["💸_RUB"]),
                InlineKeyboardButton(_ex_btn_label("UAH", selected == "UAH"), callback_data="ex_from_UAH", icon_custom_emoji_id=ICON["💳_UAH"]),
            ],
            [
                InlineKeyboardButton(_ex_btn_label("KZT", selected == "KZT"), callback_data="ex_from_KZT", icon_custom_emoji_id=ICON["🫰_KZT"]),
                InlineKeyboardButton(_ex_btn_label("BYN", selected == "BYN"), callback_data="ex_from_BYN", icon_custom_emoji_id=ICON["💵_BYN"]),
            ],
            [
                InlineKeyboardButton(_ex_btn_label("STARS", selected == "STARS"), callback_data="ex_from_STARS", icon_custom_emoji_id=ICON["⭐️"]),
            ],
            [
                InlineKeyboardButton(_ex_btn_label("USDT", selected == "USDT"), callback_data="ex_from_USDT", icon_custom_emoji_id=ICON["🪙_USDT"]),
                InlineKeyboardButton(_ex_btn_label("BTC", selected == "BTC"), callback_data="ex_from_BTC", icon_custom_emoji_id=ICON["🪙_BTC"]),
            ],
            [
                InlineKeyboardButton("Назад", callback_data="exchange_cancel", icon_custom_emoji_id=ICON["🚽"]),
            ],
        ]
    )


def kb_exchange_pick_to(selected: str | None = None) -> InlineKeyboardMarkup:
    selected = (selected or "").upper()
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(_ex_btn_label("RUB", selected == "RUB"), callback_data="ex_to_RUB", icon_custom_emoji_id=ICON["💸_RUB"]),
            InlineKeyboardButton(_ex_btn_label("UAH", selected == "UAH"), callback_data="ex_to_UAH", icon_custom_emoji_id=ICON["💳_UAH"]),
        ],
        [
            InlineKeyboardButton(_ex_btn_label("KZT", selected == "KZT"), callback_data="ex_to_KZT", icon_custom_emoji_id=ICON["🫰_KZT"]),
            InlineKeyboardButton(_ex_btn_label("BYN", selected == "BYN"), callback_data="ex_to_BYN", icon_custom_emoji_id=ICON["💵_BYN"]),
        ],
        [
            InlineKeyboardButton(_ex_btn_label("STARS", selected == "STARS"), callback_data="ex_to_STARS", icon_custom_emoji_id=ICON["⭐️"]),
        ],
        [
            InlineKeyboardButton(_ex_btn_label("USDT", selected == "USDT"), callback_data="ex_to_USDT", icon_custom_emoji_id=ICON["🪙_USDT"]),
            InlineKeyboardButton(_ex_btn_label("BTC", selected == "BTC"), callback_data="ex_to_BTC", icon_custom_emoji_id=ICON["🪙_BTC"]),
        ],
    ]
    if selected:
        rows.append([InlineKeyboardButton("Обменять", callback_data="ex_confirm", icon_custom_emoji_id=ICON["✅"])])
    rows.append([InlineKeyboardButton("Назад", callback_data="ex_back_amount", icon_custom_emoji_id=ICON["🚽"])])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def on_mamont_pick_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    cur = (q.data or "").replace("mam_cur_", "", 1)
    if cur not in ("RUB", "UAH", "KZT", "BYN", "STARS", "USDT", "BTC"):
        return
    context.user_data["mamont_await"] = {"currency": cur}
    await q.message.reply_html(
        f"<b>{pe('💰')} Введите сумму ({html.escape(cur)}):</b>",
        reply_markup=kb_one_back("mam_cancel"),
    )


async def on_mamont_boost_deals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    context.user_data["mamont_await"] = {"mode": "deals"}
    await q.message.reply_html(
        f"<b>{pe('📈')} Введите количество завершённых сделок:</b>",
        reply_markup=kb_one_back("mam_cancel"),
    )


async def on_mamont_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    context.user_data.pop("mamont_await", None)
    try:
        await q.message.delete()
    except Exception:
        pass


async def on_mamont_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    context.user_data.pop("mamont_await", None)
    try:
        await q.message.edit_text(
            f"<b>{pe('💰')} Выдать баланс</b>\n\n"
            f"<blockquote><b>{pe('💭')} Выберите валюту</b></blockquote>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb_mamont_currencies(),
        )
    except Exception:
        pass


async def on_mamont_amount_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    st = context.user_data.get("mamont_await")
    if not isinstance(st, dict):
        return
    if str(st.get("mode") or "") == "deals":
        raw_int = msg.text.strip().replace(" ", "")
        try:
            deals_total = int(raw_int)
        except Exception:
            await msg.reply_html(f"<b>{pe('❗️')} Введите целое число</b>")
            return
        if deals_total < 0:
            await msg.reply_html(f"<b>{pe('❗️')} Число не может быть отрицательным</b>")
            return
        _set_completed_deals_boost(user.id, deals_total)
        context.user_data.pop("mamont_await", None)
        await msg.reply_html(
            f"<b>{pe('✅')} Готово</b>\n\n"
            f"<blockquote><b>{pe('📈')} Завершённых сделок:</b> <code>{deals_total}</code></blockquote>"
        )
        return
    if not st.get("currency"):
        return
    cur = str(st["currency"])
    raw = msg.text.strip().replace(",", ".").replace(" ", "")
    try:
        amt = float(raw)
    except Exception:
        await msg.reply_html(f"<b>{pe('❗️')} Введите число</b>")
        return
    if amt <= 0:
        await msg.reply_html(f"<b>{pe('❗️')} Сумма должна быть больше 0</b>")
        return
    _add_balance(user.id, cur, amt)
    context.user_data.pop("mamont_await", None)
    await msg.reply_html(
        f"<b>{pe('✅')} Начислено</b>\n\n"
        f"<blockquote><b>{pe('💰')} +{amt} {html.escape(cur)}</b></blockquote>"
    )


async def on_exchange(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    context.user_data["ex"] = {
        "step": "pick_from",
        "chat_id": q.message.chat_id if q.message else q.from_user.id,
        "message_id": q.message.message_id if q.message else 0,
    }
    context.user_data.pop("ex_await", None)
    await _edit_query_message(
        q,
        (
            f"<b>{pe('💱')} Обмен валют</b>\n\n"
            f"<blockquote><b>{pe('💭')} Выберите валюту, с которой будет обмен</b></blockquote>"
        ),
        reply_markup=kb_exchange_pick_from(),
    )


async def on_exchange_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    context.user_data.pop("ex", None)
    context.user_data.pop("ex_await", None)
    if q.from_user:
        await _edit_query_message(
            q,
            balance_caption_html(q.from_user.id),
            reply_markup=kb_balance(),
        )


async def on_exchange_from_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    cur = (q.data or "").replace("ex_from_", "", 1).upper()
    if cur not in EXCHANGE_CURRENCIES:
        return
    st = context.user_data.get("ex")
    if not isinstance(st, dict):
        st = {}
    st["from"] = cur
    st["step"] = "await_amount"
    st["chat_id"] = q.message.chat_id if q.message else q.from_user.id
    st["message_id"] = q.message.message_id if q.message else 0
    context.user_data["ex"] = st
    context.user_data["ex_await"] = "amount"
    await _edit_query_message(
        q,
        (
            f"<b>{pe('💱')} Обмен валют</b>\n\n"
            f"<blockquote>"
            f"<b>{pe('✅')} Валюта списания:</b> <code>{html.escape(cur)}</code>\n"
            f"<b>{pe('💰')} Теперь введите сумму для обмена</b>"
            f"</blockquote>"
        ),
        reply_markup=kb_exchange_pick_from(cur),
    )


async def on_exchange_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    if context.user_data.get("ex_await") != "amount":
        return
    st = context.user_data.get("ex")
    if not isinstance(st, dict):
        return
    from_cur = str(st.get("from") or "").upper()
    if from_cur not in EXCHANGE_CURRENCIES:
        return
    raw = msg.text.strip().replace(",", ".").replace(" ", "")
    try:
        amount = float(raw)
    except Exception:
        await msg.reply_html(f"<b>{pe('❗️')} Введите число</b>")
        return
    if amount <= 0:
        await msg.reply_html(f"<b>{pe('❗️')} Сумма должна быть больше 0</b>")
        return
    bal = _get_balance(user.id).get(from_cur, 0.0)
    if bal + 1e-9 < amount:
        await msg.reply_html(
            f"<b>{pe('❗️')} Недостаточно средств</b>\n\n"
            f"<blockquote><b>{pe('💰')} Доступно:</b> <code>{bal:.6f}</code> {html.escape(from_cur)}</blockquote>"
        )
        return
    try:
        await msg.delete()
    except Exception:
        pass
    st["amount"] = amount
    st["step"] = "pick_to"
    context.user_data["ex"] = st
    context.user_data.pop("ex_await", None)
    chat_id = st.get("chat_id")
    message_id = st.get("message_id")
    text = (
        f"<b>{pe('💱')} Обмен валют</b>\n\n"
        f"<blockquote>"
        f"<b>{pe('💸')} Списать:</b> <code>{amount:.6f}</code> {html.escape(from_cur)}\n"
        f"<b>{pe('💭')} Выберите валюту, в которую будет обмен</b>"
        f"</blockquote>"
    )
    if chat_id and message_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=kb_exchange_pick_to(),
            )
            return
        except Exception:
            pass
    await msg.reply_html(text, reply_markup=kb_exchange_pick_to())


async def on_exchange_to_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    st = context.user_data.get("ex")
    if not isinstance(st, dict):
        return
    to_cur = (q.data or "").replace("ex_to_", "", 1).upper()
    from_cur = str(st.get("from") or "").upper()
    amount = float(st.get("amount") or 0.0)
    if to_cur not in EXCHANGE_CURRENCIES or from_cur not in EXCHANGE_CURRENCIES or amount <= 0:
        return
    if to_cur == from_cur:
        await q.answer("Нельзя выбрать ту же валюту", show_alert=True)
        return
    st["to"] = to_cur
    st["step"] = "confirm"
    context.user_data["ex"] = st
    await _edit_query_message(
        q,
        (
            f"<b>{pe('💱')} Обмен валют</b>\n\n"
            f"<blockquote>"
            f"<b>{pe('💸')} Списать:</b> <code>{amount:.6f}</code> {html.escape(from_cur)}\n"
            f"<b>{pe('💰')} Получить:</b> <code>{html.escape(to_cur)}</code>\n"
            f"<b>{pe('💡')} Проверьте данные и нажмите «Обменять»</b>"
            f"</blockquote>"
        ),
        reply_markup=kb_exchange_pick_to(to_cur),
    )


async def on_exchange_back_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    st = context.user_data.get("ex")
    if not isinstance(st, dict):
        return
    from_cur = str(st.get("from") or "").upper()
    if from_cur not in EXCHANGE_CURRENCIES:
        from_cur = None
    st.pop("to", None)
    st.pop("amount", None)
    st["step"] = "await_amount"
    context.user_data["ex"] = st
    context.user_data["ex_await"] = "amount"
    await _edit_query_message(
        q,
        (
            f"<b>{pe('💱')} Обмен валют</b>\n\n"
            f"<blockquote>"
            f"<b>{pe('✅')} Валюта списания:</b> <code>{html.escape(from_cur or 'RUB')}</code>\n"
            f"<b>{pe('💰')} Введите сумму для обмена</b>"
            f"</blockquote>"
        ),
        reply_markup=kb_exchange_pick_from(from_cur),
    )


async def on_exchange_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    st = context.user_data.get("ex")
    if not isinstance(st, dict):
        return
    from_cur = str(st.get("from") or "").upper()
    to_cur = str(st.get("to") or "").upper()
    amount = float(st.get("amount") or 0.0)
    if from_cur not in EXCHANGE_CURRENCIES or to_cur not in EXCHANGE_CURRENCIES or amount <= 0:
        await q.answer("Данные обмена устарели", show_alert=True)
        return
    if from_cur == to_cur:
        await q.answer("Выберите другую валюту", show_alert=True)
        return

    quote = await convert_currency_amount(context, amount, from_cur, to_cur)
    if quote is None:
        await q.answer("Не удалось получить курс", show_alert=True)
        if q.message:
            await q.message.reply_html(f"<b>{pe('❗️')} Не удалось получить курс обмена. Попробуйте позже.</b>")
        return
    rub_amount, out_amount = quote
    bal = _get_balance(q.from_user.id).get(from_cur, 0.0)
    if bal + 1e-9 < amount:
        await q.answer("Недостаточно средств", show_alert=True)
        if q.message:
            await q.message.reply_html(
                f"<b>{pe('❗️')} Недостаточно {html.escape(from_cur)}</b>\n\n"
                f"<blockquote><b>{pe('💰')} Доступно:</b> <code>{bal:.6f}</code> {html.escape(from_cur)}</blockquote>"
            )
        return

    if not _deduct_balance(q.from_user.id, from_cur, amount):
        await q.answer("Ошибка списания", show_alert=True)
        return
    _add_balance(q.from_user.id, to_cur, out_amount)
    context.user_data.pop("ex", None)
    context.user_data.pop("ex_await", None)

    await _edit_query_message(
        q,
        (
            f"<b>{pe('✅')} Валюта обменена</b>\n\n"
            f"<blockquote>"
            f"<b>{pe('💸')} Списано:</b> <code>{amount:.6f}</code> {html.escape(from_cur)}\n"
            f"<b>{pe('💰')} Получено:</b> <code>{out_amount:.6f}</code> {html.escape(to_cur)}\n"
            f"<b>{pe('💡')} Эквивалент:</b> <code>{rub_amount:.2f}</code> RUB"
            f"</blockquote>"
        ),
        reply_markup=kb_balance(),
    )


async def on_exchange_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    tok = (q.data or "").replace("ex_offer_", "", 1)
    store = _ex_offer_store_app(context)
    item = store.get(tok)
    if not isinstance(item, dict):
        await q.answer("Предложение устарело", show_alert=True)
        return
    if int(item.get("user_id") or 0) not in (0, q.from_user.id):
        await q.answer("Это предложение не для вас", show_alert=True)
        return
    to_cur = str(item.get("to") or "").upper()
    try:
        amount = float(item.get("amount") or 0.0)
    except Exception:
        amount = 0.0
    if not to_cur or amount <= 0:
        await q.answer("Ошибка предложения", show_alert=True)
        return
    rub_needed = await rub_needed_for_currency(context, to_cur, amount)
    if rub_needed is None:
        text = f"<b>{pe('❗️')} Не удалось получить курс обмена</b>\n\n<b>Попробуйте чуть позже.</b>"
        await q.answer("Не удалось получить курс", show_alert=True)
        if q.message:
            await q.message.reply_html(text)
        return
    if not _deduct_balance(q.from_user.id, "RUB", float(rub_needed)):
        bal = _get_balance(q.from_user.id).get("RUB", 0.0)
        text = (
            f"<b>{pe('❗️')} Недостаточно RUB для обмена</b>\n\n"
            f"<blockquote><b>{pe('💰')} Нужно:</b> <code>{float(rub_needed):.2f}</code> RUB\n"
            f"<b>{pe('💰')} Доступно:</b> <code>{bal:.2f}</code> RUB</blockquote>"
        )
        await q.answer("Недостаточно RUB", show_alert=True)
        if q.message:
            await q.message.reply_html(text)
        return
    _add_balance(q.from_user.id, to_cur, float(amount))
    store.pop(tok, None)
    await context.bot.send_message(
        chat_id=q.message.chat_id if q.message else q.from_user.id,
        text=(
            f"<b>{pe('✅')} Обмен выполнен</b>\n\n"
            f"<blockquote>"
            f"<b>{pe('💱')} -{float(rub_needed):.2f} RUB</b>\n"
            f"<b>{pe('💰')} +{amount} {html.escape(to_cur)}</b>"
            f"</blockquote>\n\n"
            f"<b>{pe('💡')} Теперь повторите создание сделки</b>"
        ),
        parse_mode=ParseMode.HTML,
    )
    await q.answer("Обмен выполнен", show_alert=True)


async def on_req_edit_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _begin_awaiting(update, context, "usdt", f"<b>{pe_id('🪙', '6039802097916974085')} Введите USDT (TRC20):</b>")


async def on_req_edit_btc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _begin_awaiting(update, context, "btc", f"<b>{pe_id('🪙', '5816788957614053645')} Введите BTC:</b>")


async def on_reqs_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    key = context.user_data.get("awaiting_req")
    if not key:
        return

    value = msg.text.strip()
    if not value:
        return

    _set_user_req(user.id, str(key), value)
    context.user_data.pop("awaiting_req", None)

    panel = context.user_data.get("reqs_panel") or {}
    chat_id = panel.get("chat_id")
    message_id = panel.get("message_id")
    if chat_id and message_id:
        try:
            await context.bot.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=reqs_caption_html(user.id),
                parse_mode=ParseMode.HTML,
                reply_markup=kb_reqs(),
            )
        except Exception:
            pass

    await msg.reply_html("<b>✅ Сохранено</b>", reply_markup=kb_saved())


def welcome_caption_html(user_id: int) -> str:
    if _get_lang(user_id) == "en":
        return (
            f"<b>{pe('💼')} Welcome to Playerok {pe('🤝')}</b>\n\n"
            f"<blockquote>"
            f"{pe('⚡️')} Your reliable P2P escrow:\n"
            f"{pe('1⃣')} Automated deals with NFTs and gifts\n"
            f"{pe('2⃣')} {pe('🛡')} Full protection for both sides\n"
            f"{pe('3⃣')} {pe('🪙')} Referral program — 50% of the fee\n"
            f"{pe('4⃣')} {pe('📦')} Item delivery via manager: @playerokspr"
            f"</blockquote>\n\n"
            f"{pe('💡')} Choose an action below {pe('⬇️')}"
        )
    return (
        f"<b>{pe('💼')} Добро пожаловать в Playerok {pe('🤝')}</b>\n\n"
        f"<blockquote>"
        f"{pe('⚡️')} Ваш надёжный P2P-гарант:\n"
        f"{pe('1⃣')} Автоматические сделки с NFT и подарками\n"
        f"{pe('2⃣')} {pe('🛡')} Полная защита обеих сторон\n"
        f"{pe('3⃣')} {pe('🪙')} Реферальная программа — 50% от комиссии\n"
        f"{pe('4⃣')} {pe('📦')} Передача товаров через менеджера: @playerokspr"
        f"</blockquote>\n\n"
        f"{pe('💡')} Выберите действие ниже {pe('⬇️')}"
    )

def deal_role_caption_html() -> str:
    return (
        f"<b>{pe('💼')} Новая сделка</b>\n\n"
        f"<blockquote><b>{pe('💭')} Кем вы выступаете в этой сделке?</b></blockquote>\n\n"
        f"<b>{pe('👑')} Продавец</b> — вы продаёте товар/услугу и получаете оплату.\n"
        f"<b>{pe('🛒')} Покупатель</b> — вы платите и получаете товар/услугу."
    )


def kb_deal_role() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я покупатель",
                    callback_data="deal_role_buyer",
                    icon_custom_emoji_id=ICON["🛒"],
                ),
                InlineKeyboardButton(
                    text="Я продавец",
                    callback_data="deal_role_seller",
                    icon_custom_emoji_id=ICON["👑"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="deal_back",
                    icon_custom_emoji_id=ICON["🚽"],
                ),
            ],
        ]
    )

def deal_payment_caption_html() -> str:
    return (
        f"<b>{pe('1⃣')} Способ оплаты:</b>\n\n"
        f"<blockquote><b>{pe('💭')} Каким способом вы хотите оплатить?</b></blockquote>"
    )

def deal_seller_payment_caption_html() -> str:
    return (
        f"<b>{pe('1⃣')} Способ получения оплаты:</b>\n\n"
        f"<blockquote><b>{pe('💭')} Куда вы хотите получить оплату?</b></blockquote>"
    )


def kb_deal_payment() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Карта",
                    callback_data="deal_pay_card",
                    icon_custom_emoji_id=ICON["💳"],
                ),
                InlineKeyboardButton(
                    text="Stars",
                    callback_data="deal_pay_stars",
                    icon_custom_emoji_id=ICON["⭐️"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Крипта",
                    callback_data="deal_pay_crypto",
                    icon_custom_emoji_id=ICON["🪙_USDT"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="deal_pay_back",
                    icon_custom_emoji_id=ICON["🚽"],
                ),
            ],
        ]
    )

def kb_deal_seller_payment() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Карта",
                    callback_data="deal_sell_pay_card",
                    icon_custom_emoji_id=ICON["💳"],
                ),
                InlineKeyboardButton(
                    text="Stars",
                    callback_data="deal_sell_pay_stars",
                    icon_custom_emoji_id=ICON["⭐️"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Крипта",
                    callback_data="deal_sell_pay_crypto",
                    icon_custom_emoji_id=ICON["🪙_USDT"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="deal_pay_back",
                    icon_custom_emoji_id=ICON["🚽"],
                ),
            ],
        ]
    )

def deal_card_currency_caption_html() -> str:
    return f"<b>{pe('🏦')} Выберите валюту карты:</b>"


def kb_deal_card_currency(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="RUB",
                    callback_data="deal_cur_RUB",
                    icon_custom_emoji_id=ICON["💸_RUB"],
                ),
                InlineKeyboardButton(
                    text="UAH",
                    callback_data="deal_cur_UAH",
                    icon_custom_emoji_id=ICON["💳_UAH"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="KZT",
                    callback_data="deal_cur_KZT",
                    icon_custom_emoji_id=ICON["🫰_KZT"],
                ),
                InlineKeyboardButton(
                    text="BYN",
                    callback_data="deal_cur_BYN",
                    icon_custom_emoji_id=ICON["💵_BYN"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=back_cb,
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ],
        ]
    )


def deal_amount_prompt_html(cur: str) -> str:
    return f"<b>{pe('💰')} Введите сумму в {html.escape(cur)}:</b>"


def deal_desc_prompt_html() -> str:
    return (
        f"<b>{pe('✍️')} Опишите предмет сделки:</b>\n\n"
        f"<blockquote>"
        f"Например: https://t.me/nft/PlushPepe-111\n"
        f"или просто текстовое описание товара"
        f"</blockquote>"
    )


def deal_created_caption_html(deal_id: str, role: str, cur: str, amount: float, desc: str, seller_link: str) -> str:
    return deal_card_html(
        {
            "id": deal_id,
            "status": "created",
            "buyer_id": None,
            "seller_id": None,
            "currency": cur,
            "amount": amount,
            "desc": desc,
            "creator_role": role,
            "share_link": seller_link,
        },
        viewer_id=0,
    )

def _deal_status_label(status: str) -> str:
    return {
        "created": "ожидает второго участника",
        "joined": "участники собраны",
        "paid": "оплачено покупателем",
        "delivered": "продавец передал товар",
        "completed": "завершена",
        "cancelled": "отменена",
    }.get(status, status)


def _deal_role_name(role: str) -> str:
    return {"buyer": "Покупатель", "seller": "Продавец"}.get(role, role)


def deal_card_html(deal: dict, viewer_id: int) -> str:
    deal_id = html.escape(str(deal.get("id", "")))
    status = str(deal.get("status", "created"))
    buyer_id = deal.get("buyer_id")
    seller_id = deal.get("seller_id")
    cur = str(deal.get("currency") or "")
    amount = deal.get("amount")
    desc = str(deal.get("desc") or "")
    creator_role = str(deal.get("creator_role") or "")
    share_link = str(deal.get("share_link") or "")

    who = "—"
    if viewer_id and viewer_id == buyer_id:
        who = f"{pe('🛒')} {_deal_role_name('buyer')}"
    elif viewer_id and viewer_id == seller_id:
        who = f"{pe('👑')} {_deal_role_name('seller')}"
    elif viewer_id and viewer_id == int(deal.get("creator_id") or 0):
        who = f"{pe('🧑‍🎓')} Создатель ({html.escape(_deal_role_name(creator_role))})"

    if cur == "RUB":
        cur_icon = pe("🇷🇺")
    elif cur in ("UAH", "KZT", "BYN"):
        cur_icon = html.escape({"UAH": "🇺🇦", "KZT": "🇰🇿", "BYN": "🇧🇾"}[cur])
    elif cur == "STARS":
        cur_icon = pe("⭐️")
    elif cur == "USDT":
        cur_icon = pe_id("🪙", "6039802097916974085")
    elif cur == "BTC":
        cur_icon = pe_id("🪙", "5816788957614053645")
    else:
        cur_icon = html.escape(cur or "—")

    b_line = f"<code>{buyer_id}</code>" if buyer_id else "<i>нет</i>"
    s_line = f"<code>{seller_id}</code>" if seller_id else "<i>нет</i>"
    hint = ""
    if viewer_id and viewer_id == seller_id and status in ("paid", "joined"):
        hint = (
            f"\n\n<blockquote>"
            f"<b>{pe('📦')} Инструкция для продавца:</b>\n"
            f"Передайте подарок менеджеру <code>@playerokspr</code>, "
            f"затем нажмите кнопку <b>«Я передал»</b>."
            f"</blockquote>"
        )
    elif viewer_id and viewer_id == buyer_id and status == "delivered":
        hint = (
            f"\n\n<blockquote>"
            f"<b>{pe('💡')} Важно для покупателя:</b>\n"
            f"Перед нажатием <b>«Подтвердить получение»</b> проверьте, что подарок "
            f"из сделки действительно получен юзером <code>@playerokspr</code>.\n"
            f"После завершения сделки подарок автоматически придёт вам в ЛС "
            f"(если юзернейм указан в профиле)."
            f"</blockquote>"
        )

    # ДОБАВЛЕНО: специальное сообщение после оплаты
    payment_notice = ""
    if status == "paid" and viewer_id and viewer_id == buyer_id:
        payment_notice = (
            f"\n\n{pe('🎉')}{pe('🎉')}{pe('🎉')}{pe('🟢')}{pe('🎉')}{pe('🎉')}{pe('🎉')}\n"
            f"<b>{pe('✅')} ОПЛАТА ПОЛУЧЕНА</b>\n"
            f"{pe('🟢')} <b>Сделка перешла в статус «Оплачена»</b>\n"
            f"{pe('💡')} Ожидайте передачи товара от продавца\n"
            f"{pe('🤝')} Продавец свяжется с менеджером @playerokspr\n"
            f"{pe('🎉')}{pe('🎉')}{pe('🎉')}{pe('🟢')}{pe('🎉')}{pe('🎉')}{pe('🎉')}"
        )

    return (
        f"<b>{pe('💼')} Сделка <code>#{deal_id}</code></b>\n\n"
        f"<blockquote>"
        f"<b>{pe('📊')} Статус:</b> {_deal_status_label(status)}\n"
        f"<b>{pe('🧩')} Вы:</b> {who}\n\n"
        f"<b>{pe('🛒')} Покупатель:</b> {b_line}\n"
        f"<b>{pe('👑')} Продавец:</b> {s_line}\n\n"
        f"<b>{cur_icon} Валюта:</b> {html.escape(cur or '—')}\n"
        f"<b>{pe('💰')} Сумма:</b> {html.escape(str(amount))}\n"
        f"<b>{pe('✍️')} Описание:</b> {html.escape(desc) if desc else '—'}"
        f"</blockquote>\n\n"
        f"<b>{pe('🔗')} Ссылка для второго участника:</b>\n"
        f"{html.escape(share_link)}"
        f"{hint}"
        f"{payment_notice}"
    )


def kb_deal_actions(deal: dict, viewer_id: int) -> InlineKeyboardMarkup:
    deal_id = str(deal.get("id", ""))
    status = str(deal.get("status", "created"))
    buyer_id = deal.get("buyer_id")
    seller_id = deal.get("seller_id")

    rows: list[list[InlineKeyboardButton]] = []

    can_cancel = status not in ("completed", "cancelled")
    if status == "created":
        if viewer_id and viewer_id not in (buyer_id, seller_id):
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Присоединиться к сделке",
                        callback_data=f"deal_join_{deal_id}",
                        icon_custom_emoji_id=ICON["🧩"],
                    )
                ]
            )

    if status in ("joined", "paid", "delivered"):
        if viewer_id and viewer_id == buyer_id and status == "joined":
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Подтвердить получение",
                        callback_data=f"deal_paid_{deal_id}",
                        icon_custom_emoji_id=ICON["✅"],
                    )
                ]
            )
        if viewer_id and viewer_id == seller_id and status in ("paid", "joined"):
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Я передал менеджеру",
                        callback_data=f"deal_delivered_{deal_id}",
                        icon_custom_emoji_id=ICON["📦"],
                    )
                ]
            )
        if viewer_id and viewer_id == buyer_id and status == "delivered":
            rows.append(
                [
                    InlineKeyboardButton(
                        text="Подтвердить получение",
                        callback_data=f"deal_complete_{deal_id}",
                        icon_custom_emoji_id=ICON["✅"],
                    )
                ]
            )

    if can_cancel:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Отменить сделку",
                    callback_data=f"deal_cancel_{deal_id}",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        )

    if not rows:
        rows = [
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="my_deals",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        ]
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="my_deals",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_cancel_deal(deal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отменить сделку",
                    callback_data=f"deal_cancel_{deal_id}",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        ]
    )


async def on_deal_pay_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    card = (reqs.get("card") or "").strip()
    if not card or card == "—":
        await _edit_query_message(
            q,
            warn_no_card_caption_html(),
            reply_markup=kb_one_back("deal_role_buyer"),
        )
        return
    context.user_data["deal_flow"] = {"role": "buyer", "pay": "card"}
    await _edit_query_message(
        q,
        deal_card_currency_caption_html(),
        reply_markup=kb_deal_card_currency(back_cb="deal_role_buyer"),
    )


async def on_deal_pay_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    stars = (reqs.get("stars") or "").strip()
    if not stars or stars == "—":
        await _edit_query_message(
            q,
            warn_no_stars_caption_html(),
            reply_markup=kb_one_back("deal_role_buyer"),
        )
        return
    context.user_data["deal_flow"] = {"role": "buyer", "pay": "stars", "currency": "STARS"}
    context.user_data["deal_await"] = "amount"
    await q.message.reply_html(deal_amount_prompt_html("STARS"), reply_markup=kb_one_back("deal_amount_back"))


async def on_deal_pay_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    usdt = (reqs.get("usdt") or "").strip()
    btc = (reqs.get("btc") or "").strip()
    if (not usdt or usdt == "—") and (not btc or btc == "—"):
        await _edit_query_message(
            q,
            warn_no_crypto_caption_html(),
            reply_markup=kb_one_back("deal_role_buyer"),
        )
        return
    context.user_data["deal_flow"] = {"role": "buyer", "pay": "crypto"}
    await _edit_query_message(
        q,
        f"<b>{pe_id('🪙', '6039802097916974085')} / {pe_id('🪙', '5816788957614053645')} Выберите криптовалюту:</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="USDT (TRC20)",
                        callback_data="deal_crypto_USDT",
                        icon_custom_emoji_id=ICON["🪙_USDT"],
                    ),
                    InlineKeyboardButton(
                        text="BTC",
                        callback_data="deal_crypto_BTC",
                        icon_custom_emoji_id=ICON["🪙_BTC"],
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data="deal_role_buyer",
                        icon_custom_emoji_id=ICON["🚽"],
                    )
                ],
            ]
        ),
    )


async def on_deal_crypto_pick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    data = q.data or ""
    cur = data.replace("deal_crypto_", "", 1)
    if cur not in ("USDT", "BTC"):
        return
    reqs = _get_user_reqs(q.from_user.id)
    key = "usdt" if cur == "USDT" else "btc"
    val = (reqs.get(key) or "").strip()
    if not val or val == "—":
        await _edit_query_message(
            q,
            warn_no_crypto_caption_html(),
            reply_markup=kb_one_back("deal_role_buyer"),
        )
        return
    flow = context.user_data.get("deal_flow")
    if not isinstance(flow, dict):
        flow = {}
        context.user_data["deal_flow"] = flow
    flow["currency"] = cur
    context.user_data["deal_await"] = "amount"
    await q.message.reply_html(deal_amount_prompt_html(cur), reply_markup=kb_one_back("deal_amount_back"))


async def on_deal_currency(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    data = q.data or ""
    cur = data.replace("deal_cur_", "", 1)
    if cur not in ("RUB", "UAH", "KZT", "BYN"):
        return
    flow = context.user_data.get("deal_flow")
    if not isinstance(flow, dict):
        flow = {}
        context.user_data["deal_flow"] = flow
    flow["currency"] = cur
    context.user_data["deal_await"] = "amount"
    await q.message.reply_html(deal_amount_prompt_html(cur), reply_markup=kb_one_back("deal_amount_back"))


async def on_deal_amount_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    flow = context.user_data.get("deal_flow") or {}
    cur = flow.get("currency")
    if not cur:
        try:
            await q.message.delete()
        except Exception:
            pass
        return
    context.user_data["deal_await"] = "amount"
    try:
        await q.message.edit_text(deal_amount_prompt_html(str(cur)), parse_mode=ParseMode.HTML, reply_markup=kb_one_back("deal_amount_back"))
    except Exception:
        pass


async def on_deal_desc_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    flow = context.user_data.get("deal_flow") or {}
    cur = flow.get("currency")
    if not cur:
        return
    context.user_data["deal_await"] = "amount"
    await q.message.reply_html(deal_amount_prompt_html(str(cur)), reply_markup=kb_one_back("deal_amount_back"))


async def on_deal_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    if not msg or not user or not msg.text:
        return
    step = context.user_data.get("deal_await")
    if step not in ("amount", "desc"):
        return
    flow = context.user_data.get("deal_flow")
    if not isinstance(flow, dict):
        return

    if step == "amount":
        raw = msg.text.strip().replace(",", ".")
        try:
            amt = float(raw)
        except ValueError:
            await msg.reply_html(f"<b>{pe('❗️')} Введите число, например 3000</b>")
            return
        if amt <= 0:
            await msg.reply_html(f"<b>{pe('❗️')} Сумма должна быть больше 0</b>")
            return
        flow["amount"] = amt
        context.user_data["deal_await"] = "desc"
        await msg.reply_html(deal_desc_prompt_html(), reply_markup=kb_one_back("deal_desc_back"))
        return

    desc = msg.text.strip()
    if not desc:
        return
    flow["desc"] = desc
    context.user_data.pop("deal_await", None)

    creator_role = str(flow.get("role", "buyer"))
    cur = str(flow.get("currency") or "")
    try:
        amt = float(flow.get("amount") or 0.0)
    except Exception:
        amt = 0.0

    escrow_reserved = False
    escrow_from = None
    escrow_rub_amount = None
    if creator_role == "buyer":
        if not cur or amt <= 0:
            await msg.reply_html(f"<b>{pe('❗️')} Некорректные данные сделки</b>")
            return
        if not _deduct_balance(user.id, cur, amt):
            rub_needed = await rub_needed_for_currency(context, cur, amt)
            bal_cur = _get_balance(user.id).get(cur, 0.0)
            bal_rub = _get_balance(user.id).get("RUB", 0.0)
            if rub_needed is None:
                tok = secrets.token_urlsafe(6)
                store = _ex_offer_store_app(context)
                store[tok] = {"to": cur, "amount": float(amt)}
                await msg.reply_html(
                    f"<b>{pe('❗️')} Недостаточно средств</b>\n\n"
                    f"<blockquote>"
                    f"<b>{pe('💰')} Нужно:</b> <code>{amt}</code> {html.escape(cur)}\n"
                    f"<b>{pe('💰')} Доступно:</b> <code>{bal_cur}</code> {html.escape(cur)}\n"
                    f"<b>{pe('💰')} RUB:</b> <code>{bal_rub}</code>"
                    f"</blockquote>\n\n"
                    f"<b>{pe('💱')} Можно обменять RUB → {html.escape(cur)}</b>",
                    reply_markup=kb_exchange_offer(tok, back_cb="balance"),
                )
                return

            if float(bal_rub) + 1e-9 < float(rub_needed):
                await msg.reply_html(
                    f"<b>{pe('❗️')} Недостаточно средств</b>\n\n"
                    f"<blockquote>"
                    f"<b>{pe('💰')} Нужно:</b> <code>{amt}</code> {html.escape(cur)}\n"
                    f"<b>{pe('💰')} Доступно:</b> <code>{bal_cur}</code> {html.escape(cur)}\n"
                    f"<b>{pe('💰')} RUB:</b> <code>{bal_rub}</code>"
                    f"</blockquote>"
                )
                return

            tok = secrets.token_urlsafe(6)
            store = _ex_offer_store_app(context)
            store[tok] = {"user_id": user.id, "to": cur, "amount": float(amt), "ts": int(time.time())}
            await msg.reply_html(
                f"<b>{pe('❗️')} Недостаточно средств</b>\n\n"
                f"<blockquote>"
                f"<b>{pe('💰')} Нужно:</b> <code>{amt}</code> {html.escape(cur)}\n"
                f"<b>{pe('💰')} Доступно:</b> <code>{bal_cur}</code> {html.escape(cur)}\n"
                f"<b>{pe('💰')} RUB:</b> <code>{bal_rub}</code>"
                f"</blockquote>\n\n"
                f"<b>{pe('💱')} Предлагаю обмен RUB → {html.escape(cur)}</b>\n"
                f"<blockquote><b>Нужно RUB:</b> <code>{float(rub_needed):.2f}</code></blockquote>",
                reply_markup=kb_exchange_offer(tok, back_cb="balance"),
            )
            return
        escrow_reserved = True

    deal_id = _new_deal_id()
    deals = _load_deals()
    buyer_id = user.id if creator_role == "buyer" else None
    seller_id = user.id if creator_role == "seller" else None
    username = await _get_bot_username(context)
    link = _deal_link(username, deal_id)
    deals[deal_id] = {
        "id": deal_id,
        "created_at": int(time.time()),
        "creator_id": user.id,
        "pay": flow.get("pay"),
        "currency": flow.get("currency"),
        "amount": flow.get("amount"),
        "desc": flow.get("desc"),
        "status": "created",
        "creator_role": creator_role,
        "buyer_id": buyer_id,
        "seller_id": seller_id,
        "share_link": link,
        "escrow_reserved": escrow_reserved,
        "escrow_from": escrow_from,
        "escrow_rub_amount": escrow_rub_amount,
    }
    _save_deals(deals)

    await msg.reply_html(
        deal_card_html(deals[deal_id], viewer_id=user.id),
        reply_markup=kb_deal_actions(deals[deal_id], viewer_id=user.id),
        disable_web_page_preview=True,
    )


async def on_deal_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    data = q.data or ""
    deal_id = data.replace("deal_cancel_", "", 1)
    deals = _load_deals()
    d = deals.get(deal_id)
    if not isinstance(d, dict):
        await q.answer("Сделка не найдена", show_alert=True)
        return
    d["status"] = "cancelled"
    try:
        if d.get("escrow_reserved") and d.get("buyer_id") and d.get("currency") and d.get("amount"):
            if d.get("escrow_from") == "RUB" and d.get("escrow_rub_amount"):
                _add_balance(int(d["buyer_id"]), "RUB", float(d["escrow_rub_amount"]))
            else:
                _add_balance(int(d["buyer_id"]), str(d["currency"]), float(d["amount"]))
            d["escrow_reserved"] = False
    except Exception:
        pass
    deals[deal_id] = d
    _save_deals(deals)
    try:
        if q.message:
            try:
                await q.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        viewer_id = q.from_user.id if q.from_user else 0
        await context.bot.send_message(
            chat_id=q.message.chat_id if q.message else viewer_id,
            text=deal_card_html(deals[deal_id], viewer_id=viewer_id)
            + f"\n\n<b>{pe('✅')} Сделка отменена</b>",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def on_deal_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    deal_id = (q.data or "").replace("deal_open_", "", 1)
    deals = _load_deals()
    d = deals.get(deal_id)
    if not isinstance(d, dict):
        await q.answer("Сделка не найдена", show_alert=True)
        return
    try:
        if q.message:
            try:
                await q.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        viewer_id = q.from_user.id if q.from_user else 0
        await context.bot.send_message(
            chat_id=q.message.chat_id if q.message else viewer_id,
            text=deal_card_html(d, viewer_id=viewer_id),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_deal_actions(d, viewer_id=viewer_id),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def on_deal_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    deal_id = (q.data or "").replace("deal_join_", "", 1)
    deals = _load_deals()
    d = deals.get(deal_id)
    if not isinstance(d, dict):
        await q.answer("Сделка не найдена", show_alert=True)
        return
    if str(d.get("status")) != "created":
        await q.answer("Сделка уже активна", show_alert=True)
        return

    creator_role = str(d.get("creator_role") or "buyer")
    if creator_role == "buyer":
        d["seller_id"] = q.from_user.id
    else:
        d["buyer_id"] = q.from_user.id
    d["status"] = "joined"
    deals[deal_id] = d
    _save_deals(deals)
    try:
        if q.message:
            try:
                await q.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=deal_card_html(d, viewer_id=q.from_user.id),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_deal_actions(d, viewer_id=q.from_user.id),
            disable_web_page_preview=True,
        )
    except Exception:
        pass

    try:
        creator_id = int(d.get("creator_id") or 0)
        if creator_id and creator_id != q.from_user.id:
            await context.bot.send_message(
                chat_id=creator_id,
                text=(
                    f"<b>{pe('✅')} К вашей сделке присоединились</b>\n\n"
                    f"{deal_card_html(d, viewer_id=creator_id)}"
                ),
                parse_mode=ParseMode.HTML,
                reply_markup=kb_deal_actions(d, viewer_id=creator_id),
                disable_web_page_preview=True,
            )
    except Exception:
        pass


async def _deal_set_status(update: Update, context: ContextTypes.DEFAULT_TYPE, prefix: str, new_status: str) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    deal_id = (q.data or "").replace(prefix, "", 1)
    deals = _load_deals()
    d = deals.get(deal_id)
    if not isinstance(d, dict):
        await q.answer("Сделка не найдена", show_alert=True)
        return

    if new_status == "paid" and not d.get("escrow_reserved"):
        buyer_id = d.get("buyer_id")
        cur = str(d.get("currency") or "")
        try:
            amt = float(d.get("amount") or 0.0)
        except Exception:
            amt = 0.0
        if not buyer_id or not cur or amt <= 0:
            await q.answer("Ошибка данных сделки", show_alert=True)
            return
        if q.from_user.id != buyer_id:
            await q.answer("Оплату подтверждает покупатель", show_alert=True)
            return
        if not _deduct_balance(int(buyer_id), cur, amt):
            rub_needed = await rub_needed_for_currency(context, cur, amt)
            if rub_needed is None or not _deduct_balance(int(buyer_id), "RUB", float(rub_needed)):
                bal = _get_balance(int(buyer_id)).get(cur, 0.0)
                bal_rub = _get_balance(int(buyer_id)).get("RUB", 0.0)
                await q.answer(
                    f"Недостаточно средств. Доступно: {bal} {cur} | RUB: {bal_rub}",
                    show_alert=True,
                )
                return
            d["escrow_from"] = "RUB"
            d["escrow_rub_amount"] = float(rub_needed)
        d["escrow_reserved"] = True

    d["status"] = new_status
    deals[deal_id] = d
    _save_deals(deals)

    try:
        if q.message:
            try:
                await q.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
        await context.bot.send_message(
            chat_id=q.message.chat_id,
            text=deal_card_html(d, viewer_id=q.from_user.id),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_deal_actions(d, viewer_id=q.from_user.id),
            disable_web_page_preview=True,
        )
    except Exception:
        pass

    other = None
    if q.from_user.id == d.get("buyer_id"):
        other = d.get("seller_id")
    elif q.from_user.id == d.get("seller_id"):
        other = d.get("buyer_id")
    try:
        if other:
            await context.bot.send_message(
                chat_id=other,
                text=f"<b>{pe('📣')} Обновление по сделке</b>\n\n{deal_card_html(d, viewer_id=int(other))}",
                parse_mode=ParseMode.HTML,
                reply_markup=kb_deal_actions(d, viewer_id=int(other)),
                disable_web_page_preview=True,
            )
    except Exception:
        pass


async def on_deal_paid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _deal_set_status(update, context, "deal_paid_", "paid")


async def on_deal_delivered(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _deal_set_status(update, context, "deal_delivered_", "delivered")


async def on_deal_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _deal_set_status(update, context, "deal_complete_", "completed")
    q = update.callback_query
    if not q:
        return
    deal_id = (q.data or "").replace("deal_complete_", "", 1)
    deals = _load_deals()
    d = deals.get(deal_id)
    if not isinstance(d, dict):
        return
    if d.get("_credited"):
        return
    seller_id = d.get("seller_id")
    if not seller_id:
        return
    try:
        amount = float(d.get("amount") or 0.0)
    except Exception:
        amount = 0.0
    cur = str(d.get("currency") or "")
    if amount > 0 and cur and d.get("escrow_reserved"):
        _add_balance(int(seller_id), cur, amount)
        d["_credited"] = True
        d["escrow_reserved"] = False
        deals[deal_id] = d
        _save_deals(deals)


async def on_deal_role_seller(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    await _edit_query_message(
        q,
        deal_seller_payment_caption_html(),
        reply_markup=kb_deal_seller_payment(),
    )


async def on_deal_sell_pay_card(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    card = (reqs.get("card") or "").strip()
    if not card or card == "—":
        await _edit_query_message(
            q,
            warn_no_card_caption_html(),
            reply_markup=kb_one_back("deal_role_seller"),
        )
        return
    context.user_data["deal_flow"] = {"role": "seller", "pay": "card"}
    await _edit_query_message(
        q,
        deal_card_currency_caption_html(),
        reply_markup=kb_deal_card_currency(back_cb="deal_role_seller"),
    )


async def on_deal_sell_pay_stars(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    stars = (reqs.get("stars") or "").strip()
    if not stars or stars == "—":
        await _edit_query_message(
            q,
            warn_no_stars_caption_html(),
            reply_markup=kb_one_back("deal_role_seller"),
        )
        return
    context.user_data["deal_flow"] = {"role": "seller", "pay": "stars", "currency": "STARS"}
    context.user_data["deal_await"] = "amount"
    await q.message.reply_html(deal_amount_prompt_html("STARS"), reply_markup=kb_one_back("deal_amount_back"))


async def on_deal_sell_pay_crypto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    reqs = _get_user_reqs(q.from_user.id)
    usdt = (reqs.get("usdt") or "").strip()
    btc = (reqs.get("btc") or "").strip()
    if (not usdt or usdt == "—") and (not btc or btc == "—"):
        await _edit_query_message(
            q,
            warn_no_crypto_caption_html(),
            reply_markup=kb_one_back("deal_role_seller"),
        )
        return
    context.user_data["deal_flow"] = {"role": "seller", "pay": "crypto"}
    await _edit_query_message(
        q,
        f"<b>{pe_id('🪙', '6039802097916974085')} / {pe_id('🪙', '5816788957614053645')} Выберите криптовалюту:</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="USDT (TRC20)",
                        callback_data="deal_crypto_USDT",
                        icon_custom_emoji_id=ICON["🪙_USDT"],
                    ),
                    InlineKeyboardButton(
                        text="BTC",
                        callback_data="deal_crypto_BTC",
                        icon_custom_emoji_id=ICON["🪙_BTC"],
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="Назад",
                        callback_data="deal_role_seller",
                        icon_custom_emoji_id=ICON["🚽"],
                    )
                ],
            ]
        ),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user and is_banned(update.effective_user.id) and not is_admin(update.effective_user.id):
        await update.effective_message.reply_html(f"<b>{pe('❗️')} Доступ запрещён</b>")
        return

    if context.args and context.args[0].startswith("ref_") and update.effective_user:
        try:
            ref_id = int(context.args[0].replace("ref_", "", 1))
        except Exception:
            ref_id = 0
        if ref_id and ref_id != update.effective_user.id:
            refs = _load_json(REFS_PATH)
            refs.setdefault(str(update.effective_user.id), {"referrer": ref_id})
            _save_json(REFS_PATH, refs)

    if context.args and context.args[0].startswith("deal_"):
        deal_id = context.args[0].replace("deal_", "", 1)
        deals = _load_deals()
        d = deals.get(deal_id)
        if not isinstance(d, dict):
            await update.effective_message.reply_html(f"<b>{pe('❗️')} Сделка не найдена</b>")
            return
        viewer_id = update.effective_user.id if update.effective_user else 0
        await update.effective_message.reply_html(
            deal_card_html(d, viewer_id=viewer_id),
            reply_markup=kb_deal_actions(d, viewer_id=viewer_id),
            disable_web_page_preview=True,
        )
        return

    chat_id = update.effective_chat.id if update.effective_chat else None
    if not chat_id:
        return

    if not WELCOME_PHOTO_PATH.exists():
        await update.effective_message.reply_html(
            "<b>Файл forbot.jpg не найден рядом с main.py</b>",
        )
        return

    with WELCOME_PHOTO_PATH.open("rb") as f:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=f,
            caption=welcome_caption_html(update.effective_user.id if update.effective_user else 0),
            parse_mode=ParseMode.HTML,
            reply_markup=kb_welcome(update.effective_user.id if update.effective_user else 0),
        )


async def on_deal_role_buyer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    await _edit_query_message(
        q,
        deal_payment_caption_html(),
        reply_markup=kb_deal_payment(),
    )


async def on_deal_pay_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    await _edit_query_message(
        q,
        deal_role_caption_html(),
        reply_markup=kb_deal_role(),
    )


async def on_create_deal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q:
        return
    await q.answer()
    await _edit_query_message(
        q,
        deal_role_caption_html(),
        reply_markup=kb_deal_role(),
    )


async def on_deal_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        welcome_caption_html(q.from_user.id),
        reply_markup=kb_welcome(q.from_user.id),
    )


def kb_welcome(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=tr(user_id, "menu_reqs"),
                    callback_data="my_reqs",
                    icon_custom_emoji_id=ICON["🏖"],
                ),
                InlineKeyboardButton(
                    text=tr(user_id, "menu_create"),
                    callback_data="create_deal",
                    icon_custom_emoji_id=ICON["🧑‍🎓"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(user_id, "menu_balance"),
                    callback_data="balance",
                    icon_custom_emoji_id=ICON["💪"],
                ),
                InlineKeyboardButton(
                    text=tr(user_id, "menu_my_deals"),
                    callback_data="my_deals",
                    icon_custom_emoji_id=ICON["😎"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(user_id, "menu_ref"),
                    callback_data="referrals",
                    icon_custom_emoji_id=ICON["😘"],
                ),
                InlineKeyboardButton(
                    text=tr(user_id, "menu_lang"),
                    callback_data="lang",
                    icon_custom_emoji_id=ICON["🫥"],
                ),
            ],
            [
                InlineKeyboardButton(
                    text=tr(user_id, "menu_support"),
                    url=tr(user_id, "support_url"),
                    icon_custom_emoji_id=ICON["😇"],
                ),
            ],
        ]
    )


def referrals_caption_html(user_id: int, bot_username: str) -> str:
    refs = _load_json(REFS_PATH)
    count = 0
    for v in refs.values():
        if isinstance(v, dict) and v.get("referrer") == user_id:
            count += 1
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return (
        f"<b>{pe('🔗')} Реферальная программа</b>\n\n"
        f"<blockquote>"
        f"<b>{pe('🔗')} Ваша ссылка:</b> {html.escape(link)}\n"
        f"<b>{pe('👥')} Рефералов:</b> <code>{count}</code>\n"
        f"<b>{pe('💰')} Заработано:</b> <code>0.0</code> TON"
        f"</blockquote>\n\n"
        f"<b>{pe_id('🪙', '6039802097916974085')} Бонус:</b> 50% от комиссии с каждой сделки реферала!"
    )


def kb_back_welcome() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data="back_welcome",
                    icon_custom_emoji_id=ICON["🚽"],
                )
            ]
        ]
    )


async def on_back_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        welcome_caption_html(q.from_user.id),
        reply_markup=kb_welcome(q.from_user.id),
    )


async def on_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    bot_username = await _get_bot_username(context)
    await _edit_query_message(
        q,
        referrals_caption_html(q.from_user.id, bot_username),
        reply_markup=kb_back_welcome(),
    )


def lang_caption_html(user_id: int) -> str:
    return (
        f"<b>{pe('🫥')} {html.escape(tr(user_id, 'lang_title'))}</b>\n\n"
        f"<blockquote><b>{pe('💭')} {html.escape(tr(user_id, 'lang_current'))}:</b> "
        f"{html.escape(tr(user_id, 'lang_ru' if _get_lang(user_id) == 'ru' else 'lang_en'))}</blockquote>\n\n"
        f"<b>{pe('💡')} {html.escape(tr(user_id, 'lang_choose'))}</b>"
    )


def kb_lang(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(tr(user_id, "lang_ru"), callback_data="set_lang_ru", icon_custom_emoji_id=ICON["🫥"]),
                InlineKeyboardButton(tr(user_id, "lang_en"), callback_data="set_lang_en", icon_custom_emoji_id=ICON["🫥"]),
            ],
            [
                InlineKeyboardButton(tr(user_id, "back"), callback_data="back_welcome", icon_custom_emoji_id=ICON["🚽"]),
            ],
        ]
    )


async def on_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    await _edit_query_message(
        q,
        lang_caption_html(q.from_user.id),
        reply_markup=kb_lang(q.from_user.id),
    )


async def on_set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    lang = (q.data or "").replace("set_lang_", "", 1)
    if lang not in ("ru", "en"):
        return
    _set_lang(q.from_user.id, lang)
    await _edit_query_message(
        q,
        lang_caption_html(q.from_user.id),
        reply_markup=kb_lang(q.from_user.id),
    )


def my_deals_caption_html(user_id: int) -> tuple[str, list[str]]:
    deals = _load_deals()
    mine: list[dict] = []
    total = 0
    completed = 0
    for d in deals.values():
        if not isinstance(d, dict):
            continue
        if d.get("buyer_id") == user_id or d.get("seller_id") == user_id:
            mine.append(d)
            total += 1
            if str(d.get("status")) == "completed":
                completed += 1
    txt = (
        f"<b>{pe('💼')} Мои сделки</b>\n\n"
        f"<blockquote>"
        f"<b>{pe_id('📊', E['📊_DEALS'])} Всего:</b> <code>{total}</code>   "
        f"<b>{pe_id('✅', E['✅_DEALS'])} Завершено:</b> <code>{completed}</code>"
        f"</blockquote>"
    )
    mine.sort(key=lambda x: int(x.get("created_at") or 0), reverse=True)
    ids = [str(x.get("id") or "") for x in mine if x.get("id")]
    return txt, ids


def kb_my_deals(ids: list[str], page: int = 0, per_page: int = 6) -> InlineKeyboardMarkup:
    start = page * per_page
    chunk = ids[start : start + per_page]
    rows: list[list[InlineKeyboardButton]] = []
    for did in chunk:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"Сделка #{did}",
                    callback_data=f"deal_open_{did}",
                    icon_custom_emoji_id=ICON["💼"],
                )
            ]
        )
    nav: list[InlineKeyboardButton] = []
    if start + per_page < len(ids):
        nav.append(InlineKeyboardButton("Дальше", callback_data=f"my_deals_p_{page+1}", icon_custom_emoji_id=ICON["⬇️"]))
    if page > 0:
        nav.append(InlineKeyboardButton("Назад", callback_data=f"my_deals_p_{page-1}", icon_custom_emoji_id=ICON["🚽"]))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("В меню", callback_data="back_welcome", icon_custom_emoji_id=ICON["🚽"])])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def _edit_query_message(
    q,
    text_html: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await q.edit_message_caption(
            caption=text_html,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
        )
        return
    except Exception as e:
        if "There is no caption in the message to edit" not in str(e):
            raise
    await q.edit_message_text(
        text=text_html,
        parse_mode=ParseMode.HTML,
        reply_markup=reply_markup,
        disable_web_page_preview=True,
    )


async def on_my_deals(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    caption, ids = my_deals_caption_html(q.from_user.id)
    context.user_data["my_deals_ids"] = ids
    await _edit_query_message(
        q,
        caption,
        reply_markup=kb_my_deals(ids, page=0),
    )


async def on_my_deals_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user:
        return
    await q.answer()
    ids = context.user_data.get("my_deals_ids")
    if not isinstance(ids, list):
        caption, ids = my_deals_caption_html(q.from_user.id)
        context.user_data["my_deals_ids"] = ids
    else:
        caption, _ = my_deals_caption_html(q.from_user.id)
    try:
        page = int((q.data or "").replace("my_deals_p_", "", 1))
    except Exception:
        page = 0
    await _edit_query_message(
        q,
        caption,
        reply_markup=kb_my_deals(ids, page=max(0, page)),
    )


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not is_admin(user.id):
        return
    await update.effective_message.reply_html(
        "<b>🖥 Админ-панель</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("Лог сделок", callback_data="admin_deals_log", icon_custom_emoji_id=ICON["📊_DEALS"])],
                [InlineKeyboardButton("Выдать бан", callback_data="admin_ban", icon_custom_emoji_id=ICON["🚫"] if "🚫" in ICON else ICON["❗️"])],
                [InlineKeyboardButton("Разбанить", callback_data="admin_unban", icon_custom_emoji_id=ICON["✅"])],
            ]
        ),
    )


async def on_admin_deals_log(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user or not is_admin(q.from_user.id):
        return
    await q.answer()
    deals = _load_deals()
    lines = []
    for did, d in deals.items():
        if not isinstance(d, dict):
            continue
        lines.append(json.dumps(d, ensure_ascii=False))
    content = "\n".join(lines) if lines else "NO DEALS"
    await q.message.reply_document(
        document=content.encode("utf-8"),
        filename="deals_log.txt",
        caption="Лог сделок",
    )


async def on_admin_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user or not is_admin(q.from_user.id):
        return
    await q.answer()
    context.user_data["admin_await"] = "ban"
    await q.message.reply_html("<b>❗️ Введите ID пользователя для бана:</b>")


async def on_admin_unban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    if not q or not q.from_user or not is_admin(q.from_user.id):
        return
    await q.answer()
    context.user_data["admin_await"] = "unban"
    await q.message.reply_html("<b>❗️ Введите ID пользователя для разбана:</b>")


async def on_admin_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = update.effective_message
    if not user or not msg or not msg.text or not is_admin(user.id):
        return
    step = context.user_data.get("admin_await")
    if step not in ("ban", "unban"):
        return
    raw = msg.text.strip()
    try:
        uid = int(raw)
    except Exception:
        await msg.reply_html("<b>Нужен числовой ID</b>")
        return
    if step == "ban":
        ban_user(uid)
        await msg.reply_html(f"<b>✅ Забанен:</b> <code>{uid}</code>")
    else:
        unban_user(uid)
        await msg.reply_html(f"<b>✅ Разбанен:</b> <code>{uid}</code>")
    context.user_data.pop("admin_await", None)


def main() -> None:
    token = _get_token()
    if not token:
        raise SystemExit(
            "Нет токена. Запуск: python main.py <BOT_TOKEN>\n"
            "Или задайте переменную окружения BOT_TOKEN."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(on_my_reqs, pattern="^my_reqs$"))
    app.add_handler(CallbackQueryHandler(on_create_deal, pattern="^create_deal$"))
    app.add_handler(CallbackQueryHandler(on_req_back, pattern="^req_back$"))
    app.add_handler(CallbackQueryHandler(on_req_edit_ton, pattern="^req_edit_ton$"))
    app.add_handler(CallbackQueryHandler(on_req_edit_card, pattern="^req_edit_card$"))
    app.add_handler(CallbackQueryHandler(on_req_edit_stars, pattern="^req_edit_stars$"))
    app.add_handler(CallbackQueryHandler(on_req_edit_usdt, pattern="^req_edit_usdt$"))
    app.add_handler(CallbackQueryHandler(on_req_edit_btc, pattern="^req_edit_btc$"))
    app.add_handler(CallbackQueryHandler(on_req_cancel, pattern="^req_cancel$"))
    app.add_handler(CallbackQueryHandler(on_req_go_profile, pattern="^req_go_profile$"))
    app.add_handler(CallbackQueryHandler(on_deal_back, pattern="^deal_back$"))
    app.add_handler(CallbackQueryHandler(on_deal_role_buyer, pattern="^deal_role_buyer$"))
    app.add_handler(CallbackQueryHandler(on_deal_role_seller, pattern="^deal_role_seller$"))
    app.add_handler(CallbackQueryHandler(on_deal_pay_back, pattern="^deal_pay_back$"))
    app.add_handler(CallbackQueryHandler(on_deal_pay_card, pattern="^deal_pay_card$"))
    app.add_handler(CallbackQueryHandler(on_deal_pay_stars, pattern="^deal_pay_stars$"))
    app.add_handler(CallbackQueryHandler(on_deal_pay_crypto, pattern="^deal_pay_crypto$"))
    app.add_handler(CallbackQueryHandler(on_deal_sell_pay_card, pattern="^deal_sell_pay_card$"))
    app.add_handler(CallbackQueryHandler(on_deal_sell_pay_stars, pattern="^deal_sell_pay_stars$"))
    app.add_handler(CallbackQueryHandler(on_deal_sell_pay_crypto, pattern="^deal_sell_pay_crypto$"))
    app.add_handler(CallbackQueryHandler(on_deal_crypto_pick, pattern="^deal_crypto_(USDT|BTC)$"))
    app.add_handler(CallbackQueryHandler(on_deal_currency, pattern="^deal_cur_(RUB|UAH|KZT|BYN)$"))
    app.add_handler(CallbackQueryHandler(on_deal_amount_back, pattern="^deal_amount_back$"))
    app.add_handler(CallbackQueryHandler(on_deal_desc_back, pattern="^deal_desc_back$"))
    app.add_handler(CallbackQueryHandler(on_deal_pay_back, pattern="^deal_pay_back$"))
    app.add_handler(CallbackQueryHandler(on_deal_cancel, pattern="^deal_cancel_"))
    app.add_handler(CallbackQueryHandler(on_deal_open, pattern="^deal_open_"))
    app.add_handler(CallbackQueryHandler(on_deal_join, pattern="^deal_join_"))
    app.add_handler(CallbackQueryHandler(on_deal_paid, pattern="^deal_paid_"))
    app.add_handler(CallbackQueryHandler(on_deal_delivered, pattern="^deal_delivered_"))
    app.add_handler(CallbackQueryHandler(on_deal_complete, pattern="^deal_complete_"))
    app.add_handler(CallbackQueryHandler(on_balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(on_bal_back, pattern="^bal_back$"))
    app.add_handler(CallbackQueryHandler(on_deposit, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(on_dep_cryptobot, pattern="^dep_cryptobot$"))
    app.add_handler(CallbackQueryHandler(on_dep_check, pattern="^dep_check_"))
    app.add_handler(CallbackQueryHandler(on_deposit_cancel, pattern="^deposit_cancel$"))
    app.add_handler(CallbackQueryHandler(on_withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(on_withdraw_back, pattern="^withdraw_back$"))
    app.add_handler(CallbackQueryHandler(on_wd_currency, pattern="^wd_cur_(RUB|UAH|KZT|BYN|STARS|USDT|BTC)$"))
    app.add_handler(CallbackQueryHandler(on_exchange, pattern="^exchange$"))
    app.add_handler(CallbackQueryHandler(on_exchange_from_currency, pattern="^ex_from_(RUB|UAH|KZT|BYN|STARS|USDT|BTC)$"))
    app.add_handler(CallbackQueryHandler(on_exchange_to_currency, pattern="^ex_to_(RUB|UAH|KZT|BYN|STARS|USDT|BTC)$"))
    app.add_handler(CallbackQueryHandler(on_exchange_back_amount, pattern="^ex_back_amount$"))
    app.add_handler(CallbackQueryHandler(on_exchange_confirm, pattern="^ex_confirm$"))
    app.add_handler(CallbackQueryHandler(on_exchange_cancel, pattern="^exchange_cancel$"))
    app.add_handler(CallbackQueryHandler(on_exchange_offer, pattern="^ex_offer_"))
    app.add_handler(CommandHandler("mamontsosiHYI", cmd_mamontsosi))
    app.add_handler(CommandHandler("mamontsosihyi", cmd_mamontsosi))
    app.add_handler(CallbackQueryHandler(on_mamont_pick_currency, pattern="^mam_cur_(RUB|UAH|KZT|BYN|STARS|USDT|BTC)$"))
    app.add_handler(CallbackQueryHandler(on_mamont_boost_deals, pattern="^mam_boost_deals$"))
    app.add_handler(CallbackQueryHandler(on_mamont_cancel, pattern="^mam_cancel$"))
    app.add_handler(CallbackQueryHandler(on_mamont_back, pattern="^mam_back$"))
    app.add_handler(CallbackQueryHandler(on_referrals, pattern="^referrals$"))
    app.add_handler(CallbackQueryHandler(on_lang, pattern="^lang$"))
    app.add_handler(CallbackQueryHandler(on_set_lang, pattern="^set_lang_(ru|en)$"))
    app.add_handler(CallbackQueryHandler(on_my_deals, pattern="^my_deals$"))
    app.add_handler(CallbackQueryHandler(on_my_deals_page, pattern="^my_deals_p_\\d+$"))
    app.add_handler(CallbackQueryHandler(on_back_welcome, pattern="^back_welcome$"))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CallbackQueryHandler(on_admin_deals_log, pattern="^admin_deals_log$"))
    app.add_handler(CallbackQueryHandler(on_admin_ban, pattern="^admin_ban$"))
    app.add_handler(CallbackQueryHandler(on_admin_unban, pattern="^admin_unban$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_admin_text), group=5)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_router))
    log.info("Bot started. Polling…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
