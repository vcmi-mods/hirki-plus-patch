#!/usr/bin/env python3
r"""
HPP preflight checker.

Obsługiwane wejścia:

1. Pełny source/repo HPP:
       py tools\hpp_preflight.py
       py tools\hpp_preflight.py "C:\sciezka\do\hirki-plus-patch"

2. Folder zainstalowany przez VCMI Launcher:
       py tools\hpp_preflight.py --launcher-package \
          "C:\Users\ja\Documents\My Games\vcmi\Mods\hirki-plus-patch"

3. ZIP utworzony z folderu Launchera:
       py tools\hpp_preflight.py --launcher-package \
          "C:\sciezka\do\hirki-plus-patch.zip"

Domyslny tryb ``auto`` rozpoznaje source albo paczke Launchera.
W trybie Launcher skrypt rozpakowuje zagniezdzone ``content.zip`` tylko do
katalogu tymczasowego. Nie zmienia instalacji moda ani badanego archiwum.

Skrypt uzywa wylacznie standardowej biblioteki Pythona.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Literal


EXPECTED_ROOT_NAME = "hirki-plus-patch"
Mode = Literal["auto", "source", "launcher"]
ResolvedMode = Literal["source", "launcher"]

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


@dataclass(frozen=True)
class LauncherArchiveStats:
    archives: int = 0
    extracted_files: int = 0


@dataclass(frozen=True)
class PreparedRoot:
    input_path: Path
    root: Path
    mode: ResolvedMode
    launcher_stats: LauncherArchiveStats | None = None


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


def _validate_zip_member_name(name: str) -> PurePosixPath:
    normalized = name.replace("\\", "/")
    member = PurePosixPath(normalized)

    if not normalized:
        return member
    if member.is_absolute():
        raise ValueError(f"Niedozwolona absolutna sciezka w ZIP: {name}")
    if any(part in {"", ".", ".."} for part in member.parts):
        raise ValueError(f"Niedozwolona sciezka w ZIP: {name}")
    if member.parts and member.parts[0].endswith(":"):
        raise ValueError(f"Niedozwolona sciezka dysku w ZIP: {name}")

    return member


def safe_extract_zip(archive: zipfile.ZipFile, destination: Path) -> int:
    """Safely extract an archive and return the number of regular files."""

    destination.mkdir(parents=True, exist_ok=True)
    destination_resolved = destination.resolve()
    seen: set[str] = set()
    file_count = 0

    for info in archive.infolist():
        member = _validate_zip_member_name(info.filename)
        normalized = member.as_posix().rstrip("/")
        if normalized in seen:
            raise ValueError(f"Powtorzony wpis w ZIP: {info.filename}")
        seen.add(normalized)

        if not normalized:
            continue

        target = (destination / Path(*member.parts)).resolve()
        if target != destination_resolved and destination_resolved not in target.parents:
            raise ValueError(f"Proba wyjscia poza katalog docelowy: {info.filename}")

        if info.is_dir() or info.filename.endswith("/"):
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info, "r") as source, target.open("wb") as output:
            shutil.copyfileobj(source, output)
        file_count += 1

    return file_count


def find_hpp_root(extracted_root: Path) -> Path:
    direct = extracted_root
    if (direct / "mod.json").is_file() and (direct / "Mods").is_dir():
        return direct

    candidates: list[Path] = []
    for mod_path in extracted_root.rglob("mod.json"):
        candidate = mod_path.parent
        if (candidate / "Mods").is_dir():
            candidates.append(candidate)

    if not candidates:
        raise ValueError("Nie znaleziono root HPP z mod.json i folderem Mods.")

    minimum_depth = min(len(path.relative_to(extracted_root).parts) for path in candidates)
    shallowest = [
        path
        for path in candidates
        if len(path.relative_to(extracted_root).parts) == minimum_depth
    ]

    preferred = [path for path in shallowest if path.name == EXPECTED_ROOT_NAME]
    if len(preferred) == 1:
        return preferred[0]
    if len(shallowest) == 1:
        return shallowest[0]

    choices = ", ".join(str(path.relative_to(extracted_root)) for path in shallowest)
    raise ValueError(f"Niejednoznaczny root HPP w archiwum: {choices}")


def detect_mode(root: Path) -> ResolvedMode:
    has_source_content = (root / "Content").is_dir()
    content_archives = list(root.rglob("content.zip"))

    if has_source_content and content_archives:
        raise ValueError(
            "Niejednoznaczna struktura: znaleziono jednoczesnie root Content "
            "i content.zip. Uzyj jawnie --source albo --launcher-package."
        )
    if has_source_content:
        return "source"
    if content_archives:
        return "launcher"

    raise ValueError(
        "Nie mozna rozpoznac typu paczki: brak root Content oraz content.zip."
    )


def materialize_launcher_content(root: Path) -> LauncherArchiveStats:
    archives = sorted(root.rglob("content.zip"))
    if not archives:
        raise ValueError("Tryb Launcher: nie znaleziono zadnego content.zip.")

    extracted_files = 0
    for archive_path in archives:
        module_root = archive_path.parent
        content_root = module_root / "Content"

        if content_root.exists() and any(content_root.iterdir()):
            raise ValueError(
                "Tryb Launcher: jednoczesnie istnieja Content i content.zip w: "
                f"{module_root.relative_to(root)}"
            )

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                bad_member = archive.testzip()
                if bad_member is not None:
                    raise ValueError(
                        f"Uszkodzony wpis {bad_member} w "
                        f"{archive_path.relative_to(root)}"
                    )
                extracted_files += safe_extract_zip(archive, content_root)
        except zipfile.BadZipFile as exc:
            raise ValueError(
                f"Niepoprawny content.zip: {archive_path.relative_to(root)}: {exc}"
            ) from exc

    return LauncherArchiveStats(
        archives=len(archives),
        extracted_files=extracted_files,
    )


@contextmanager
def prepare_root(input_path: Path, requested_mode: Mode) -> Iterator[PreparedRoot]:
    input_path = input_path.expanduser().resolve()

    with tempfile.TemporaryDirectory(prefix="hpp_preflight_") as temp_name:
        temp_root = Path(temp_name)

        if input_path.is_file():
            if input_path.suffix.lower() != ".zip":
                raise ValueError(
                    f"Plik wejsciowy nie jest archiwum ZIP: {input_path}"
                )
            outer_root = temp_root / "outer"
            try:
                with zipfile.ZipFile(input_path, "r") as archive:
                    bad_member = archive.testzip()
                    if bad_member is not None:
                        raise ValueError(f"Uszkodzony wpis w ZIP: {bad_member}")
                    safe_extract_zip(archive, outer_root)
            except zipfile.BadZipFile as exc:
                raise ValueError(f"Niepoprawny ZIP: {input_path}: {exc}") from exc
            working_root = find_hpp_root(outer_root)
            mode: ResolvedMode = (
                detect_mode(working_root)
                if requested_mode == "auto"
                else requested_mode
            )

        elif input_path.is_dir():
            mode = (
                detect_mode(input_path)
                if requested_mode == "auto"
                else requested_mode
            )

            if mode == "source":
                # Source validation is read-only, so avoid copying a potentially
                # large repository (especially its .git directory).
                working_root = input_path
            else:
                copied_parent = temp_root / "directory"
                copied_parent.mkdir(parents=True, exist_ok=True)
                working_root = copied_parent / input_path.name
                shutil.copytree(
                    input_path,
                    working_root,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"),
                )

        else:
            raise ValueError(f"Nie istnieje sciezka: {input_path}")

        launcher_stats: LauncherArchiveStats | None = None
        if mode == "launcher":
            launcher_stats = materialize_launcher_content(working_root)

        yield PreparedRoot(
            input_path=input_path,
            root=working_root,
            mode=mode,
            launcher_stats=launcher_stats,
        )


def check_launcher_archives(
    stats: LauncherArchiveStats | None,
    report: Report,
) -> None:
    if stats is None:
        return
    report.ok(
        "Paczka Launchera: wszystkie content.zip sa poprawne "
        f"({stats.archives}); odczytano {stats.extracted_files} plikow."
    )


def check_root(root: Path, mode: ResolvedMode, report: Report) -> None:
    required = ("mod.json", "Content", "Mods")
    missing = [name for name in required if not (root / name).exists()]
    if missing:
        report.error(
            "Folder nie wyglada jak znormalizowany root HPP. Brakuje: "
            + ", ".join(missing)
        )
        return

    if root.name != EXPECTED_ROOT_NAME:
        report.warning(
            f'Nazwa folderu root to "{root.name}", a instalacyjna nazwa HPP '
            f'powinna brzmiec "{EXPECTED_ROOT_NAME}". '
            "Moze to zmienic ID child modow w recznej instalacji."
        )
    else:
        report.ok("Root moda ma prawidlowa nazwe hirki-plus-patch.")

    if mode == "launcher":
        report.ok(
            "Tryb Launcher dziala na tymczasowo znormalizowanej zawartosci; "
            "oryginalna paczka nie zostala zmieniona."
        )


def check_conflict_markers(root: Path, report: Report) -> None:
    found: list[str] = []
    marker_pattern = re.compile(r"^(?:<<<<<<<(?: .+)?|=======|>>>>>>>(?: .+)?)$")

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
        report.ok("Brak znacznikow konfliktu Git.")


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
        report.error("Niepoprawne pliki JSON:\n  - " + "\n  - ".join(failures))
    else:
        report.ok(f"Wszystkie pliki JSON sa poprawne ({len(json_paths)}).")

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
                    f"{mod_path.relative_to(root)}: pole {key} nie jest lista"
                )
                continue

            for relative in values:
                if not isinstance(relative, str):
                    missing.append(
                        f"{mod_path.relative_to(root)}: {key} zawiera wartosc "
                        "niebedaca stringiem"
                    )
                    continue
                checked += 1
                target = content_root / Path(relative)
                if not target.is_file():
                    missing.append(
                        f"{mod_path.relative_to(root)}: {key} -> {relative}"
                    )

        def walk_translation_nodes(node: Any) -> None:
            nonlocal checked
            if isinstance(node, dict):
                translations = node.get("translations")
                if translations is not None:
                    if not isinstance(translations, list):
                        missing.append(
                            f"{mod_path.relative_to(root)}: translations nie jest lista"
                        )
                    else:
                        for relative in translations:
                            if not isinstance(relative, str):
                                missing.append(
                                    f"{mod_path.relative_to(root)}: translations "
                                    "zawiera wartosc niebedaca stringiem"
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
            "Brakujace lub niepoprawne referencje plikowe w mod.json:\n  - "
            + "\n  - ".join(missing)
        )
    else:
        report.ok(
            f"Wszystkie referencje plikowe z mod.json istnieja ({checked})."
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
            errors.append(f"Brak zestawu tlumaczen: {language}.json")
            continue

        for key, source_paths in sorted(references.items()):
            if key not in keys:
                locations = ", ".join(str(path) for path in sorted(source_paths))
                errors.append(
                    f"{language}: brak klucza {key} uzytego w: {locations}"
                )
                continue

            values = keys[key]
            if values and all(value == "" for value in values):
                locations = ", ".join(str(path) for path in sorted(source_paths))
                errors.append(
                    f"{language}: uzywany klucz {key} ma pusta wartosc "
                    f"(ryzyko pipeline), zrodla: {locations}"
                )

    if errors:
        report.error(
            "Problemy z referencjami tlumaczen @hpp.*:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            f"Referencje @hpp.* sa kompletne i niepuste w EN/PL "
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
        configuration = faction_data["town"]["buildings"][building]["configuration"]
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
                    f'{rule["name"]}: {faction_id} ma onEmptyMessage inne niz ""'
                )

            if configuration.get("onVisitedMessage") != "":
                errors.append(
                    f'{rule["name"]}: {faction_id} ma onVisitedMessage inne niz ""'
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
            "Town rewardables nie spelniaja finalnego wzorca fallbackow:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Town rewardables maja literalne puste onEmptyMessage i "
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
            errors.append("Golden Goose: depends nie jest lista")
        elif ESTATES_DEPENDENCY not in depends:
            errors.append(
                "Golden Goose nie zalezy od "
                f"{ESTATES_DEPENDENCY}"
            )

    if errors:
        report.error(
            "Problem zaleznosci Golden Goose -> Estates:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Golden Goose poprawnie zalezy od "
            "hirki-plus-patch.skills.estates, a modul Estates istnieje."
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
                f'{rule["name"]}: English game.json nie jest ladowany przez mod.json'
            )
        if expected_polish not in polish_paths:
            errors.append(
                f'{rule["name"]}: Polish game.json nie jest ladowany przez mod.json'
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
                    f'{rule["name"]}: EN runtime key {key} pozostal w legacy translation'
                )
            if key in polish_legacy:
                errors.append(
                    f'{rule["name"]}: PL runtime key {key} pozostal w legacy translation'
                )

    if errors:
        report.error(
            "Customowe komunikaty nagrod Towns nie sa pipeline-safe:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Runtime translations Gold Halls i Resource Silos sa odseparowane "
            "od pipeline-managed hero texts w EN/PL."
        )


def normalize_launcher_description(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def check_root_launcher_descriptions(
    root: Path,
    parsed: dict[Path, Any],
    mode: ResolvedMode,
    report: Report,
) -> None:
    root_mod_path = root / "mod.json"
    root_mod = parsed.get(root_mod_path)
    errors: list[str] = []

    if not isinstance(root_mod, dict):
        report.error("Problem z rootowymi opisami Launchera: brak root mod.json")
        return

    english_runtime = normalize_launcher_description(root_mod.get("description"))
    polish_block = root_mod.get("polish")
    polish_runtime = normalize_launcher_description(
        polish_block.get("description") if isinstance(polish_block, dict) else ""
    )

    if mode == "launcher":
        if not english_runtime:
            errors.append("root mod.json nie zawiera finalnego opisu English")
        if not polish_runtime:
            errors.append("root mod.json nie zawiera finalnego opisu Polish")

        if errors:
            report.error(
                "Problem z finalnymi opisami Launchera:\n  - "
                + "\n  - ".join(errors)
            )
        else:
            report.ok(
                "Paczka Launchera zawiera niepuste finalne opisy root EN/PL "
                "w mod.json; source-only description/*.md nie sa wymagane."
            )
        return

    english_path = root / "description/english.md"
    polish_path = root / "description/polish.md"

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

    if english_runtime != english_source:
        errors.append(
            "root mod.json description rozni sie od description/english.md"
        )
    if polish_runtime != polish_source:
        errors.append(
            "root mod.json polish.description rozni sie od description/polish.md"
        )

    if errors:
        report.error(
            "Rootowe opisy Launchera nie sa zsynchronizowane:\n  - "
            + "\n  - ".join(errors)
        )
    else:
        report.ok(
            "Rootowe opisy Launchera EN/PL sa zgodne z "
            "description/english.md i description/polish.md."
        )


def print_report(prepared: PreparedRoot, report: Report) -> int:
    print("=" * 72)
    print("HPP PREFLIGHT")
    print(f"Input: {prepared.input_path}")
    print(f"Mode:  {prepared.mode}")
    print(f"Root:  {prepared.root}")
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
        description=(
            "Walidacja source HPP oraz folderow/ZIP-ow instalowanych przez "
            "VCMI Launcher."
        )
    )
    parser.add_argument(
        "root",
        nargs="?",
        type=Path,
        help=(
            "Folder root HPP albo ZIP folderu Launchera. Domyslnie katalog "
            "nadrzedny folderu tools, w ktorym znajduje sie ten skrypt."
        ),
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--launcher-package",
        dest="mode",
        action="store_const",
        const="launcher",
        help="Wymus odczyt zagniezdzonych content.zip paczki Launchera.",
    )
    mode_group.add_argument(
        "--source",
        dest="mode",
        action="store_const",
        const="source",
        help="Wymus walidacje pelnego source/repo.",
    )
    mode_group.add_argument(
        "--mode",
        dest="mode",
        choices=("auto", "source", "launcher"),
        help="Jawnie wybierz tryb; domyslnie auto.",
    )
    parser.set_defaults(mode="auto")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.root is None:
        input_path = Path(__file__).resolve().parent.parent
    else:
        input_path = args.root

    try:
        with prepare_root(input_path, args.mode) as prepared:
            report = Report()

            check_launcher_archives(prepared.launcher_stats, report)
            check_root(prepared.root, prepared.mode, report)
            check_conflict_markers(prepared.root, report)

            parsed = check_json_files(prepared.root, report)
            if parsed:
                check_mod_file_references(prepared.root, parsed, report)
                check_translation_references(prepared.root, parsed, report)
                check_forbidden_silent_empty(prepared.root, report)
                check_town_rewardables(prepared.root, parsed, report)
                check_golden_goose_estates(prepared.root, parsed, report)
                check_root_launcher_descriptions(
                    prepared.root,
                    parsed,
                    prepared.mode,
                    report,
                )
                check_pipeline_safe_town_runtime_translations(
                    prepared.root,
                    parsed,
                    report,
                )

            return print_report(prepared, report)

    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        fallback = PreparedRoot(
            input_path=input_path.expanduser().resolve(),
            root=input_path.expanduser().resolve(),
            mode="launcher" if args.mode == "launcher" else "source",
        )
        report = Report()
        report.error(str(exc))
        return print_report(fallback, report)


if __name__ == "__main__":
    sys.exit(main())
