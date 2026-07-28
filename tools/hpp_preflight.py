#!/usr/bin/env python3
r"""
HPP preflight checker.

Uruchom z katalogu głównego repo:
    py tools\hpp_preflight.py

Opcjonalnie można wskazać inny folder moda:
    py tools\hpp_preflight.py "C:\ścieżka\do\hirki-plus-patch"

Skrypt używa wyłącznie standardowej biblioteki Pythona.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


EXPECTED_ROOT_NAME = "hirki-plus-patch"

FILE_LIST_KEYS = {
    "artifacts",
    "creatures",
    "factions",
    "heroes",
    "objects",
    "skills",
    "spells",
}

TEXT_EXTENSIONS = {
    ".json",
    ".md",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}

CONFLICT_MARKERS = (
    "<<<<<<<",
    "=======",
    ">>>>>>>",
)

TOWN_RULES = (
    {
        "name": "Gold Specialist Halls",
        "relative_path": Path(
            "Mods/towns/Mods/Gold Specialist Halls/"
            "Content/config/factions/GoldSpecialistHalls.json"
        ),
        "building": "cityHall",
        "expected_count": 12,
    },
    {
        "name": "Resource Specialist Silos",
        "relative_path": Path(
            "Mods/towns/Mods/Resource Specialist Silos/"
            "Content/config/factions/ResourceSpecialistSilos.json"
        ),
        "building": "resourceSilo",
        "expected_count": 12,
    },
    {
        "name": "Elemental Ritual",
        "relative_path": Path(
            "Mods/towns/Mods/Elemental Ritual/"
            "Content/config/factions/ElementalRitual.json"
        ),
        "building": "mageGuild3",
        "expected_count": 11,
    },
)

GOLDEN_GOOSE_MOD = Path("Mods/artifacts/Mods/Golden Goose/mod.json")
ESTATES_MOD = Path("Mods/skills/Mods/Estates/mod.json")
ESTATES_DEPENDENCY = "hirki-plus-patch.skills.estates"


PIPELINE_SAFE_TOWN_TRANSLATIONS = (
    {
        "name": "Gold Specialist Halls",
        "module_root": Path("Mods/towns/Mods/Gold Specialist Halls"),
        "runtime_keys": (
            "hpp.towns.goldSpecialistHalls.cityHall",
        ),
    },
    {
        "name": "Resource Specialist Silos",
        "module_root": Path("Mods/towns/Mods/Resource Specialist Silos"),
        "runtime_keys": (
            "hpp.towns.resourceSpecialistSilos.castleWoodOre",
            "hpp.towns.resourceSpecialistSilos.rampartCrystal",
            "hpp.towns.resourceSpecialistSilos.towerGems",
            "hpp.towns.resourceSpecialistSilos.infernoMercury",
            "hpp.towns.resourceSpecialistSilos.necropolisWoodOre",
            "hpp.towns.resourceSpecialistSilos.dungeonSulfur",
            "hpp.towns.resourceSpecialistSilos.strongholdWoodOre",
            "hpp.towns.resourceSpecialistSilos.fortressWoodOre",
            "hpp.towns.resourceSpecialistSilos.confluxMercury",
            "hpp.towns.resourceSpecialistSilos.coveSulfur",
            "hpp.towns.resourceSpecialistSilos.factoryCrystal",
            "hpp.towns.resourceSpecialistSilos.bulwarkWoodOre",
        ),
    },
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self, message: str) -> None:
        self.passed.append(message)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def iter_values(value: Any) -> Iterable[Any]:
    if isinstance(value, dict):
        for child in value.values():
            yield child
            yield from iter_values(child)
    elif isinstance(value, list):
        for child in value:
            yield child
            yield from iter_values(child)


def find_nearest_module_root(path: Path, repo_root: Path) -> Path | None:
    current = path.parent
    while True:
        if (current / "mod.json").is_file():
            return current
        if current == repo_root:
            break
        if repo_root not in current.parents:
            break
        current = current.parent
    return None


def check_root(root: Path, report: Report) -> None:
    required = ("mod.json", "Content", "Mods")
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        report.error(
            "Folder nie wygląda jak root HPP. Brakuje: " + ", ".join(missing)
        )
        return

    if root.name != EXPECTED_ROOT_NAME:
        report.warning(
            f'Nazwa folderu root to "{root.name}", a instalacyjna nazwa HPP '
            f'powinna brzmieć "{EXPECTED_ROOT_NAME}". '
            "Może to zmienić ID child modów w ręcznej instalacji."
        )
    else:
        report.ok("Root moda ma prawidłową nazwę hirki-plus-patch.")


def check_conflict_markers(root: Path, report: Report) -> None:
    found: list[str] = []

    marker_pattern = re.compile(
        r"^(?:<<<<<<<(?: .+)?|=======|>>>>>>>(?: .+)?)$"
    )

    for path in root.rglob("*"):
        if ".git" in path.parts:
            continue
        if not path.is_file() or path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            if marker_pattern.fullmatch(line.strip()):
                found.append(
                    f"{path.relative_to(root)}:{line_number}: {line.strip()}"
                )

    if found:
        report.error(
            "Znaleziono znaczniki konfliktu Git:\n  - " + "\n  - ".join(found)
        )
    else:
        report.ok("Brak znaczników konfliktu Git.")


def check_json_files(root: Path, report: Report) -> dict[Path, Any]:
    parsed: dict[Path, Any] = {}
    failures: list[str] = []

    json_paths = sorted(root.rglob("*.json"))
    for path in json_paths:
        try:
            parsed[path] = read_json(path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(f"{path.relative_to(root)}: {exc}")

    if failures:
        report.error(
            "Niepoprawne pliki JSON:\n  - " + "\n  - ".join(failures)
        )
    else:
        report.ok(f"Wszystkie pliki JSON są poprawne ({len(json_paths)}).")

    return parsed


def check_mod_file_references(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    missing: list[str] = []
    checked = 0

    for mod_path in sorted(root.rglob("mod.json")):
        data = parsed.get(mod_path)
        if not isinstance(data, dict):
            continue

        module_root = mod_path.parent
        content_root = module_root / "Content"

        for key in FILE_LIST_KEYS:
            values = data.get(key)
            if values is None:
                continue
            if not isinstance(values, list):
                missing.append(
                    f"{mod_path.relative_to(root)}: pole {key} nie jest listą"
                )
                continue

            for relative in values:
                if not isinstance(relative, str):
                    missing.append(
                        f"{mod_path.relative_to(root)}: {key} zawiera wartość "
                        "niebędącą stringiem"
                    )
                    continue
                checked += 1
                target = content_root / Path(relative)
                if not target.is_file():
                    missing.append(
                        f"{mod_path.relative_to(root)}: {key} -> {relative}"
                    )

        # translation paths can occur inside language objects
        def walk_translation_nodes(node: Any) -> None:
            nonlocal checked
            if isinstance(node, dict):
                translations = node.get("translations")
                if translations is not None:
                    if not isinstance(translations, list):
                        missing.append(
                            f"{mod_path.relative_to(root)}: translations nie jest listą"
                        )
                    else:
                        for relative in translations:
                            if not isinstance(relative, str):
                                missing.append(
                                    f"{mod_path.relative_to(root)}: translations "
                                    "zawiera wartość niebędącą stringiem"
                                )
                                continue
                            checked += 1
                            target = content_root / Path(relative)
                            if not target.is_file():
                                missing.append(
                                    f"{mod_path.relative_to(root)}: "
                                    f"translations -> {relative}"
                                )

                for value in node.values():
                    walk_translation_nodes(value)
            elif isinstance(node, list):
                for value in node:
                    walk_translation_nodes(value)

        walk_translation_nodes(data)

    if missing:
        report.error(
            "Brakujące lub niepoprawne referencje plikowe w mod.json:\n  - "
            + "\n  - ".join(missing)
        )
    else:
        report.ok(
            f"Wszystkie referencje plikowe z mod.json istnieją ({checked})."
        )


def detect_translation_language(path: Path) -> str | None:
    supported = {"english", "polish"}

    if path.stem.lower() in supported:
        return path.stem.lower()

    for part in reversed(path.parts):
        lowered = part.lower()
        if lowered in supported:
            return lowered

    return None


def collect_translation_keys(
    root: Path,
    parsed: dict[Path, Any],
) -> dict[str, dict[str, list[Any]]]:
    by_language: dict[str, dict[str, list[Any]]] = {}

    for path, data in parsed.items():
        if "translation" not in {part.lower() for part in path.parts}:
            continue
        if not isinstance(data, dict):
            continue

        language = detect_translation_language(path)
        if language is None:
            continue

        target = by_language.setdefault(language, {})
        for key, value in data.items():
            target.setdefault(key, []).append(value)

    return by_language


def collect_hpp_translation_references(
    root: Path,
    parsed: dict[Path, Any],
) -> dict[str, set[Path]]:
    references: dict[str, set[Path]] = {}

    for path, data in parsed.items():
        if "translation" in {part.lower() for part in path.parts}:
            continue

        for value in iter_values(data):
            if isinstance(value, str) and value.startswith("@hpp."):
                key = value[1:]
                references.setdefault(key, set()).add(path.relative_to(root))

    return references


def check_translation_references(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    languages = collect_translation_keys(root, parsed)
    references = collect_hpp_translation_references(root, parsed)

    errors: list[str] = []

    for language in ("english", "polish"):
        keys = languages.get(language)
        if keys is None:
            errors.append(f"Brak zestawu tłumaczeń: {language}.json")
            continue

        for key, source_paths in sorted(references.items()):
            if key not in keys:
                locations = ", ".join(str(path) for path in sorted(source_paths))
                errors.append(
                    f"{language}: brak klucza {key} użytego w: {locations}"
                )
                continue

            values = keys[key]
            if values and all(value == "" for value in values):
                locations = ", ".join(str(path) for path in sorted(source_paths))
                errors.append(
                    f"{language}: używany klucz {key} ma pustą wartość "
                    f"(ryzyko pipeline), źródła: {locations}"
                )

    if errors:
        report.error(
            "Problemy z referencjami tłumaczeń @hpp.*:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            f"Referencje @hpp.* są kompletne i niepuste w EN/PL "
            f"({len(references)} unikalnych kluczy)."
        )


def check_forbidden_silent_empty(root: Path, report: Report) -> None:
    found: list[str] = []

    for path in root.rglob("*.json"):
        text = path.read_text(encoding="utf-8-sig")
        if "silentEmpty" in text:
            found.append(str(path.relative_to(root)))

    if found:
        report.error(
            "Znaleziono zakazany wzorzec silentEmpty:\n  - "
            + "\n  - ".join(found)
        )
    else:
        report.ok("Brak zakazanego wzorca silentEmpty.")


def get_building_configuration(
    faction_data: Any,
    building: str,
) -> dict[str, Any] | None:
    if not isinstance(faction_data, dict):
        return None
    try:
        configuration = (
            faction_data["town"]["buildings"][building]["configuration"]
        )
    except (KeyError, TypeError):
        return None
    return configuration if isinstance(configuration, dict) else None


def check_town_rewardables(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    errors: list[str] = []

    for rule in TOWN_RULES:
        path = root / rule["relative_path"]
        data = parsed.get(path)

        if not isinstance(data, dict):
            errors.append(f'{rule["name"]}: brak lub niepoprawny plik config')
            continue

        found_count = 0
        for faction_id, faction_data in data.items():
            configuration = get_building_configuration(
                faction_data,
                rule["building"],
            )
            if configuration is None:
                errors.append(
                    f'{rule["name"]}: brak configuration dla {faction_id} / '
                    f'{rule["building"]}'
                )
                continue

            found_count += 1

            if configuration.get("onEmptyMessage") != "":
                errors.append(
                    f'{rule["name"]}: {faction_id} ma onEmptyMessage inne niż ""'
                )

            if configuration.get("onVisitedMessage") != "":
                errors.append(
                    f'{rule["name"]}: {faction_id} ma onVisitedMessage inne niż ""'
                )

            rewards = configuration.get("rewards")
            if not isinstance(rewards, list) or not rewards:
                errors.append(
                    f'{rule["name"]}: {faction_id} nie ma niepustej listy rewards'
                )

        if found_count != rule["expected_count"]:
            errors.append(
                f'{rule["name"]}: znaleziono {found_count} konfiguracji, '
                f'oczekiwano {rule["expected_count"]}'
            )

    if errors:
        report.error(
            "Town rewardables nie spełniają finalnego wzorca fallbacków:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Town rewardables mają literalne puste onEmptyMessage i "
            "onVisitedMessage: Gold 12, Silos 12, Ritual 11."
        )


def check_golden_goose_estates(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    goose_path = root / GOLDEN_GOOSE_MOD
    estates_path = root / ESTATES_MOD

    errors: list[str] = []

    goose = parsed.get(goose_path)
    estates = parsed.get(estates_path)

    if not isinstance(goose, dict):
        errors.append(f"Brak lub niepoprawny {GOLDEN_GOOSE_MOD}")
    if not isinstance(estates, dict):
        errors.append(f"Brak lub niepoprawny {ESTATES_MOD}")

    if isinstance(goose, dict):
        depends = goose.get("depends")
        if not isinstance(depends, list):
            errors.append("Golden Goose: depends nie jest listą")
        elif ESTATES_DEPENDENCY not in depends:
            errors.append(
                "Golden Goose nie zależy od "
                f"{ESTATES_DEPENDENCY}"
            )

    if errors:
        report.error(
            "Problem zależności Golden Goose -> Estates:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Golden Goose poprawnie zależy od "
            "hirki-plus-patch.skills.estates, a moduł Estates istnieje."
        )




def check_pipeline_safe_town_runtime_translations(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    errors: list[str] = []

    for rule in PIPELINE_SAFE_TOWN_TRANSLATIONS:
        module_root = root / rule["module_root"]
        mod_path = module_root / "mod.json"
        english_game_path = (
            module_root / "Content/config/translation/hpp/english/game.json"
        )
        polish_game_path = (
            module_root / "Content/config/translation/hpp/polish/game.json"
        )
        english_legacy_path = module_root / "Content/translation/english.json"
        polish_legacy_path = module_root / "Content/translation/polish.json"

        mod_data = parsed.get(mod_path)
        english_game = parsed.get(english_game_path)
        polish_game = parsed.get(polish_game_path)
        english_legacy = parsed.get(english_legacy_path)
        polish_legacy = parsed.get(polish_legacy_path)

        if not isinstance(mod_data, dict):
            errors.append(f'{rule["name"]}: brak lub niepoprawny mod.json')
            continue

        expected_english = "config/translation/hpp/english/game.json"
        expected_polish = "config/translation/hpp/polish/game.json"

        english_block = mod_data.get("english")
        polish_block = mod_data.get("polish")
        english_paths = (
            english_block.get("translations", [])
            if isinstance(english_block, dict)
            else []
        )
        polish_paths = (
            polish_block.get("translations", [])
            if isinstance(polish_block, dict)
            else []
        )

        if expected_english not in english_paths:
            errors.append(
                f'{rule["name"]}: English game.json nie jest ładowany przez mod.json'
            )
        if expected_polish not in polish_paths:
            errors.append(
                f'{rule["name"]}: Polish game.json nie jest ładowany przez mod.json'
            )

        if not isinstance(english_game, dict):
            errors.append(f'{rule["name"]}: brak angielskiego pipeline-safe game.json')
            english_game = {}
        if not isinstance(polish_game, dict):
            errors.append(f'{rule["name"]}: brak polskiego pipeline-safe game.json')
            polish_game = {}

        if not isinstance(english_legacy, dict):
            english_legacy = {}
        if not isinstance(polish_legacy, dict):
            polish_legacy = {}

        for key in rule["runtime_keys"]:
            if not english_game.get(key):
                errors.append(
                    f'{rule["name"]}: brak niepustego EN runtime key {key} w game.json'
                )
            if not polish_game.get(key):
                errors.append(
                    f'{rule["name"]}: brak niepustego PL runtime key {key} w game.json'
                )
            if key in english_legacy:
                errors.append(
                    f'{rule["name"]}: EN runtime key {key} pozostał w legacy translation'
                )
            if key in polish_legacy:
                errors.append(
                    f'{rule["name"]}: PL runtime key {key} pozostał w legacy translation'
                )

    if errors:
        report.error(
            "Customowe komunikaty nagród Towns nie są pipeline-safe:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Runtime translations Gold Halls i Resource Silos są odseparowane "
            "od pipeline-managed hero texts w EN/PL."
        )

def normalize_launcher_description(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def check_root_launcher_descriptions(
    root: Path,
    parsed: dict[Path, Any],
    report: Report,
) -> None:
    root_mod_path = root / "mod.json"
    english_path = root / "description/english.md"
    polish_path = root / "description/polish.md"

    errors: list[str] = []

    root_mod = parsed.get(root_mod_path)
    if not isinstance(root_mod, dict):
        errors.append("Brak lub niepoprawny root mod.json")
    if not english_path.is_file():
        errors.append("Brak description/english.md")
    if not polish_path.is_file():
        errors.append("Brak description/polish.md")

    if errors:
        report.error(
            "Problem z rootowymi opisami Launchera:\n  - "
            + "\n  - ".join(errors)
        )
        return

    english_source = normalize_launcher_description(
        english_path.read_text(encoding="utf-8-sig")
    )
    polish_source = normalize_launcher_description(
        polish_path.read_text(encoding="utf-8-sig")
    )

    english_runtime = normalize_launcher_description(
        root_mod.get("description", "")
    )

    polish_block = root_mod.get("polish")
    if not isinstance(polish_block, dict):
        polish_runtime = ""
    else:
        polish_runtime = normalize_launcher_description(
            polish_block.get("description", "")
        )

    if english_runtime != english_source:
        errors.append(
            "root mod.json description różni się od description/english.md"
        )

    if polish_runtime != polish_source:
        errors.append(
            "root mod.json polish.description różni się od "
            "description/polish.md"
        )

    if errors:
        report.error(
            "Rootowe opisy Launchera nie są zsynchronizowane:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Rootowe opisy Launchera EN/PL są zgodne z "
            "description/english.md i description/polish.md."
        )

def print_report(root: Path, report: Report) -> int:
    print("=" * 72)
    print("HPP PREFLIGHT")
    print(f"Root: {root}")
    print("=" * 72)

    for message in report.passed:
        print(f"[OK]   {message}")

    for message in report.warnings:
        print(f"[WARN] {message}")

    for message in report.errors:
        print(f"[FAIL] {message}")

    print("-" * 72)
    print(
        f"Wynik: {len(report.passed)} OK, "
        f"{len(report.warnings)} WARN, "
        f"{len(report.errors)} FAIL"
    )

    if report.errors:
        print("PREFLIGHT FAILED")
        return 1

    print("PREFLIGHT PASSED")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Walidacja struktury i krytycznych regresji HPP."
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        help=(
            "Folder root HPP. Domyślnie katalog nadrzędny folderu tools, "
            "w którym znajduje się ten skrypt."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.root is None:
        root = Path(__file__).resolve().parent.parent
    else:
        root = args.root.expanduser().resolve()

    report = Report()

    if not root.is_dir():
        report.error(f"Nie istnieje folder: {root}")
        return print_report(root, report)

    check_root(root, report)
    check_conflict_markers(root, report)

    parsed = check_json_files(root, report)
    if parsed:
        check_mod_file_references(root, parsed, report)
        check_translation_references(root, parsed, report)
        check_forbidden_silent_empty(root, report)
        check_town_rewardables(root, parsed, report)
        check_golden_goose_estates(root, parsed, report)
        check_root_launcher_descriptions(root, parsed, report)
        check_pipeline_safe_town_runtime_translations(root, parsed, report)

    return print_report(root, report)


if __name__ == "__main__":
    sys.exit(main())
