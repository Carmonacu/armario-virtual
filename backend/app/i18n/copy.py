"""User-facing copy for notifications, emails and AI replies.

English stays the wording every non-Spanish locale already receives. Spanish (Spain,
informal tú) is used when the user's locale is ``es``.
"""

from datetime import date, timedelta

WEEKDAYS_ES = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")

OCCASIONS_ES = {
    "beach": "playa",
    "brunch": "brunch",
    "business-casual": "informal de oficina",
    "casual": "casual",
    "date": "cita",
    "dinner": "cena",
    "formal": "formal",
    "gym": "gimnasio",
    "hiking": "senderismo",
    "interview": "entrevista",
    "lounge": "casa",
    "office": "oficina",
    "outdoor": "aire libre",
    "party": "fiesta",
    "running": "running",
    "smart-casual": "arreglado informal",
    "sport": "deporte",
    "sporty": "deportivo",
    "travel": "viaje",
    "wedding": "boda",
    "weekend": "fin de semana",
    "work": "trabajo",
}

WEATHER_ES = {
    "sunny": "soleado",
    "mostly sunny": "mayormente soleado",
    "partly cloudy": "parcialmente nublado",
    "cloudy": "nublado",
    "foggy": "niebla",
    "light drizzle": "llovizna débil",
    "drizzle": "llovizna",
    "heavy drizzle": "llovizna intensa",
    "freezing drizzle": "llovizna helada",
    "light rain": "lluvia débil",
    "rain": "lluvia",
    "heavy rain": "lluvia intensa",
    "freezing rain": "lluvia helada",
    "light snow": "nieve débil",
    "snow": "nieve",
    "heavy snow": "nieve intensa",
    "snow grains": "cinarra",
    "light showers": "chubascos débiles",
    "showers": "chubascos",
    "heavy showers": "chubascos fuertes",
    "light snow showers": "chubascos de nieve débiles",
    "snow showers": "chubascos de nieve",
    "thunderstorm": "tormenta",
    "thunderstorm with hail": "tormenta con granizo",
    "clear": "despejado",
    "unknown": "desconocido",
}

ITEM_TYPES_ES = {
    "accessories": "accesorios",
    "bag": "bolso",
    "belt": "cinturón",
    "blazer": "blazer",
    "blouse": "blusa",
    "bodysuit": "body",
    "boots": "botas",
    "camisole": "camisola",
    "cardigan": "cárdigan",
    "coat": "abrigo",
    "dress": "vestido",
    "flats": "bailarinas",
    "hat": "sombrero",
    "heels": "tacones",
    "hoodie": "sudadera con capucha",
    "jacket": "chaqueta",
    "jeans": "vaqueros",
    "jumpsuit": "mono",
    "leggings": "leggings",
    "overalls": "peto",
    "pants": "pantalones",
    "polo": "polo",
    "poncho": "poncho",
    "sandals": "sandalias",
    "scarf": "bufanda",
    "shirt": "camisa",
    "shoes": "zapatos",
    "shorts": "pantalones cortos",
    "skirt": "falda",
    "sneakers": "zapatillas",
    "socks": "calcetines",
    "suit": "traje",
    "sweater": "jersey",
    "sweatshirt": "sudadera",
    "t-shirt": "camiseta",
    "tank-top": "camiseta de tirantes",
    "tie": "corbata",
    "tights": "medias",
    "top": "top",
    "vest": "chaleco",
    "watch": "reloj",
}

DESCRIPTION_LANGUAGES = {
    "en": "English",
    "es": "Spanish from Spain, using informal tú",
    "zh-CN": "Simplified Chinese",
    "zh-TW": "Traditional Chinese",
    "ko": "Korean",
    "ja": "Japanese",
    "fr": "French",
    "de": "German",
    "it": "Italian",
}


def is_spanish(locale: str | None) -> bool:
    return locale == "es"


def reply_language_name(locale: str | None) -> str:
    # An unknown stored locale stays in English. The UI default can be Spanish without
    # sending a garbage locale code to the model as Spanish.
    if isinstance(locale, str) and locale in DESCRIPTION_LANGUAGES:
        return DESCRIPTION_LANGUAGES[locale]
    return DESCRIPTION_LANGUAGES["en"]


def outfit_copy_instruction(locale: str | None) -> str:
    return (
        "\n\nWrite the headline, highlights and styling_tip in "
        f"{reply_language_name(locale)}. Do not translate JSON keys or item numbers."
    )


def occasion_label(occasion: str, locale: str | None) -> str:
    if is_spanish(locale):
        return OCCASIONS_ES.get(occasion, occasion.replace("-", " "))
    return occasion.replace("-", " ").title()


def weather_label(condition: str | None, locale: str | None) -> str | None:
    if condition is None or not is_spanish(locale):
        return condition
    return WEATHER_ES.get(condition.strip().lower(), condition)


def item_type_label(item_type: str, locale: str | None) -> str:
    if is_spanish(locale):
        return ITEM_TYPES_ES.get(item_type, item_type)
    return item_type


def outfit_day(scheduled_for: date | None, today: date, locale: str | None) -> tuple[str, str]:
    """Title word and the form used mid-sentence."""
    if scheduled_for is None or scheduled_for == today:
        return ("Hoy", "hoy") if is_spanish(locale) else ("Today", "today")
    if scheduled_for == today + timedelta(days=1):
        return ("Mañana", "mañana") if is_spanish(locale) else ("Tomorrow", "tomorrow")
    if is_spanish(locale):
        name = WEEKDAYS_ES[scheduled_for.weekday()]
        return name.capitalize(), name
    weekday = scheduled_for.strftime("%A")
    return weekday, weekday


def outfit_title(day_phrase: str, day_label: str, occasion: str, locale: str | None) -> str:
    if is_spanish(locale):
        link = "de" if day_phrase in ("hoy", "mañana") else "del"
        return f"Conjunto {occasion} {link} {day_phrase}"
    return f"{day_label}'s {occasion} Outfit"


def outfit_heading(day_phrase: str, day_label: str, occasion: str, locale: str | None) -> str:
    if is_spanish(locale):
        link = "de" if day_phrase in ("hoy", "mañana") else "del"
        return f"Conjunto {link} {day_phrase}: {occasion}"
    return f"{day_label}'s Outfit: {occasion}"


def outfit_greeting(for_tomorrow: bool, name: str, day_phrase: str, locale: str | None) -> str:
    if is_spanish(locale):
        hello = "Buenas tardes" if for_tomorrow else "Buenos días"
        when = day_phrase if day_phrase in ("hoy", "mañana") else f"el {day_phrase}"
        return f"{hello}, {name}. Aquí tienes la sugerencia de conjunto para {when}:"
    hello = "Good evening" if for_tomorrow else "Good morning"
    return f"{hello}, {name}! Here's your outfit suggestion for {day_phrase}:"


def tip_label(locale: str | None) -> str:
    return "Consejo" if is_spanish(locale) else "Tip"


def outfit_ready(locale: str | None) -> tuple[str, str]:
    if is_spanish(locale):
        return "Tu conjunto está listo.", "¡Tu conjunto está listo!"
    return "Your outfit is ready.", "Your outfit is ready!"


def view_outfit_label(locale: str | None) -> str:
    return "Ver conjunto" if is_spanish(locale) else "View Outfit"


def email_chrome(locale: str | None) -> dict[str, str]:
    if is_spanish(locale):
        return {
            "tip": "Consejo",
            "sent": "Enviado por Wardrowbe",
            "manage": "Gestionar los avisos",
            "forecast": " (previsión)",
            "unknown": "Desconocido",
        }
    return {
        "tip": "Tip",
        "sent": "Sent by Wardrowbe",
        "manage": "Manage notification settings",
        "forecast": " (forecast)",
        "unknown": "Unknown",
    }


def wash_reminder(count: int, summary: str, locale: str | None) -> tuple[str, str, str]:
    if is_spanish(locale):
        if count == 1:
            body = f"1 prenda necesita lavado: {summary}"
        else:
            body = f"{count} prendas necesitan lavado: {summary}"
        return "Recordatorio de lavado", body, "Ver armario"
    noun = "1 item needs" if count == 1 else f"{count} items need"
    return "Laundry Reminder", f"{noun} washing: {summary}", "View Wardrobe"


def more_items(extra: int, locale: str | None) -> str:
    if is_spanish(locale):
        return f" y {extra} más"
    return f" and {extra} more"
