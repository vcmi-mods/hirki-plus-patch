# Hirki Plus Patch (H.P.P.)

**Hirki Plus Patch (H.P.P.)** is a modular gameplay and balance patch for *Heroes of Might and Magic III* on VCMI, designed for use with **Horn of the Abyss**.

The mod focuses on making underused creatures, skills, spells, heroes, war machines, selected town buildings, selected artifacts, and selected map objects more practical and interesting while preserving the classic feel of Heroes III.

## Requirements

- VCMI 1.7.4 or newer
- Horn of the Abyss on VCMI

## This mod includes

- secondary skill improvements
- New Luck system
- New Intelligence and combat mana support
- ranged combat and war machine changes
- selected spell improvements
- selected hero updates
- selected artifact reworks and related interactions
- creature ability modules
- town building modules
- map object reward modules
- English wording cleanup
- Polish localization

## Version 1.4.0 highlights

- **Spells** — added **Ice Storm**, a level 4 Water Magic spell that damages all creatures and can freeze units that are not native to Snow terrain.
- **Skills** — added the **Leadership** module with **Inspired March**, granting additional movement after visiting adventure map objects that provide positive Morale for the next battle.
- **Luck Objects** — added four optional modules that allow the hero's **Luck** mastery to improve rewards from adventure map objects and creature banks covered by the modules:
  - **Luck Scaling for Adventure Map Objects**
  - **Creature Banks Resources**
  - **Creature Banks Units**
  - **Luck-Enhanced Pyramid Reward**
- **In-game descriptions** — improved formatting and emphasis across multiple existing modules for better readability.
- **Spell Book localization** — fixed the English names of **Mirth**, **Sorrow**, **Fortune**, **Misfortune**, and **Magic Mirror**, and moved their localized names to the appropriate child modules.
- **Leather Armor of Swiftness** — added a new fused **Relic** combining **Necklace of Swiftness**, **Ring of the Wayfarer**, and **Cape of Velocity**, providing Speed bonuses to the bearer and allied heroes.
- **Main mod description** — reorganized and rewrote the main description to present the scope of individual modules more clearly.
- **Screenshots** — added a Launcher gallery showcasing selected HPP changes and new content.

## Version 1.3.1 hotfix

- Fixed unresolved and empty town-building fallback messages in **Gold Specialist Halls**, **Resource Specialist Silos** and **Elemental Ritual**.

## Version 1.3.0 highlights

- **Artifacts** — reworked **Armageddon's Blade**.
- **Artifacts** — added **Boots of Reinforcement**, a new four-component **Relic** combination artifact.
- **Artifacts** — reworked **Golden Goose** with stacking income bonuses for each allied hero with **Estates**.
- **Artifacts** — reworked **Cornucopia** with stacking rare-resource bonuses for each allied rare-resource production specialist.
- **Spells** — added **Acid Burst**, a new level 4 Water Magic debuff spell.
- **Heroes** — added starting-army modules for standard tier 3–6 creature specialists.
- **Skills** — corrected misleading **Estates** descriptions.

## Modular design

H.P.P. is built as a modular patch. Most parts of the project are split into submodules, so players can enable the parts they want and keep the rest of their setup close to the original game.

Individual submodules include their own Launcher descriptions with more detailed mechanics, values, thresholds, and compatibility notes.

## Polish localization

H.P.P. includes Polish localization for Launcher descriptions and selected in-game texts.

The Polish localization is written to stay close to the style and terminology of the classic Polish Heroes III translation where possible.

## Installation

The recommended installation method is through the VCMI Launcher after the mod is available in the VCMI mods repository.

For manual installation, use a packaged ZIP from **GitHub Releases** when available. After extraction, make sure the installation path is:

```text
Mods/hirki-plus-patch/mod.json
```

GitHub's **Code → Download ZIP** source archives add the branch name to the extracted folder. If the folder is named, for example, `hirki-plus-patch-main` or `hirki-plus-patch-vcmi-1.7`, rename it to `hirki-plus-patch` before placing it in the VCMI `Mods` directory.

## Updates and compatibility

H.P.P. is actively maintained. Future updates may include additional modules, localization improvements, balance adjustments, bug fixes, and compatibility fixes.

Because H.P.P. changes many gameplay systems through modular submods, some conflicts with other mods may only become visible during play.

H.P.P. is modular. If another mod changes the same part of the game, you can usually disable only the corresponding H.P.P. module instead of disabling the entire patch.

H.P.P. is designed for Horn of the Abyss on VCMI. Mods that are incompatible with HotA, require HotA to be disabled, or replace HotA in a way that prevents normal HotA-based gameplay should be treated as incompatible with H.P.P. as well.

## Reporting issues

Please report bugs, compatibility issues, missing translations, or unclear descriptions through GitHub Issues:

https://github.com/vcmi-mods/hirki-plus-patch/issues

You can also contact me on the VCMI Discord server as `@bew_`, especially for quick questions or other issues with the mod.

## Polska wersja

HPP zawiera polską lokalizację opisów Launchera oraz wybranych tekstów w grze.

## Najważniejsze elementy wersji 1.4.0

- **Czary** — dodano **Lodową burzę**, czar Magii Wody 4. poziomu, który zadaje obrażenia wszystkim jednostkom i może zamrażać oddziały nienatywne dla terenu Śnieg.
- **Umiejętności** — dodano moduł **Dowodzenia** z **Natchnionym marszem**, dającym dodatkowe punkty ruchu po odwiedzeniu obiektów na mapie przygody, które zapewniają dodatnie morale na następną bitwę.
- **Obiekty szczęścia** — dodano cztery opcjonalne moduły, dzięki którym poziom **Szczęścia** bohatera może ulepszać nagrody z obiektów mapy przygody i banków stworzeń objętych modułami:
  - **Skalowanie obiektów mapy przygody przez Szczęście**
  - **Banki stworzeń — zasoby**
  - **Banki stworzeń — jednostki**
  - **Nagroda Piramidy wzmocniona przez Szczęście**
- **Opisy w grze** — ujednolicono formatowanie i wyróżnienia w opisach wielu istniejących modułów, poprawiając ich czytelność.
- **Lokalizacja Księgi zaklęć** — poprawiono przełączanie nazw czarów **Mirth**, **Sorrow**, **Fortune**, **Misfortune** i **Magic Mirror** między językiem angielskim i polskim oraz przeniesiono ich tłumaczenia do właściwych childmodów.
- **Skórzana Zbroja Szybkości** — dodano nowy złożony artefakt klasy **Relikt**, łączący **Naszyjnik Przyspieszenia**, **Pierścień Wędrowca** i **Płaszcz Zwinności**, zapewniający premie do szybkości noszącemu i sprzymierzonym bohaterom.
- **Główny opis moda** — przeorganizowano i przepisano główny opis, aby czytelniej przedstawiał zakres poszczególnych modułów.
- **Zrzuty ekranu** — dodano galerię Launchera prezentującą wybrane zmiany i nową zawartość HPP.

## Hotfix 1.3.1

- Naprawiono nierozwiązane i puste komunikaty awaryjne budynków miejskich w modułach **Specjaliści złota i Ratusze**, **Specjaliści rzadkich surowców i Magazyny zasobów** oraz **Rytuał żywiołów**.

## Najważniejsze elementy wersji 1.3.0

- **Artefakty** — przebudowano **Ostrze Armagedonu**.
- **Artefakty** — dodano **Buty Odsieczy**, nowy czteroelementowy artefakt składany klasy **Relikt**.
- **Artefakty** — przebudowano **Złotą Gęś**, dodając kumulującą się premię za każdego sprzymierzonego bohatera posiadającego **Finanse**.
- **Artefakty** — przebudowano **Miasto dobrobytu**, dodając kumulującą się premię za każdego sprzymierzonego **specjalistę w produkcji rzadkich surowców**.
- **Czary** — dodano **Żrący rozbryzg**, nowy osłabiający czar Magii Wody 4. poziomu.
- **Bohaterowie** — dodano moduły armii początkowych dla standardowych specjalistów jednostek poziomów 3–6.
- **Umiejętności** — poprawiono mylące opisy **Finansów**.

Polskie opisy są widoczne w VCMI Launcherze po wybraniu języka polskiego. Lokalizacja została przygotowana z myślą o stylu i terminologii klasycznego polskiego tłumaczenia Heroes III, o ile było to możliwe.

### Informacja o kompatybilności

HPP jest modułowy. Jeśli inny mod zmienia ten sam element gry, zazwyczaj można wyłączyć tylko odpowiedni moduł HPP zamiast całej paczki.

HPP jest projektowany pod HotA on VCMI. Mody niekompatybilne z HotA, wymagające wyłączenia HotA albo zastępujące HotA w sposób uniemożliwiający normalną grę opartą na HotA należy traktować jako niekompatybilne również z HPP.

Błędy w polskich tekstach, terminologii albo brakujące tłumaczenia najlepiej zgłaszać przez GitHub Issues:

https://github.com/vcmi-mods/hirki-plus-patch/issues

Można też kontaktować się ze mną na serwerze Discord VCMI jako `@bew_`, szczególnie w przypadku szybkich pytań albo innych nieprawidłowości z modem.

## Reuse

Feel free to reuse or adapt HPP-created content in your own VCMI mods — just credit Hirki Plus Patch.

This does not apply to third-party or game-derived material listed in `THIRD_PARTY_ASSETS.md`.

VCMI maintainers are welcome to make compatibility, translation, and repository-maintenance changes when needed.
