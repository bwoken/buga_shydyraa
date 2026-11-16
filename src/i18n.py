"""Load UTF-8 translation catalogs once per process, never on a click.

Tuvan is a draft requiring a native speaker's review. Catalogs are local
package resources; the dynamic-web client only receives displayed strings.
"""

import json
from importlib.resources import files

import locales

LANGUAGES = {"ru": "Русский", "en": "English", "tyv": "Тыва дыл *"}
MESSAGES = {language: json.loads(files(locales).joinpath(f"{language}.json").read_text(encoding="utf-8"))
            for language in LANGUAGES}


def translate(language: str, key: str, **values) -> str:
    return MESSAGES.get(language, MESSAGES["ru"])[key].format(**values)


class LocalizedError(ValueError):
    """The service supplies a key; each player picks their language."""

    def __init__(self, key):
        self.key = key
        super().__init__(translate("ru", key))
