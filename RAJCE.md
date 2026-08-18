# rajce_download.py

Stiahne všetky fotky z verejného albumu na `rajce.idnes.cz` (rajce.net) do priečinka
na disku. Používa iba štandardnú knižnicu Pythonu 3 – nič sa neinštaluje.

## Použitie

```bash
python3 rajce_download.py "https://www.rajce.idnes.cz/album/zKYw5qA7tOXZmhcK" -o fotky
```

Prepínače:

| prepínač | význam |
| --- | --- |
| `-o, --out` | cieľový priečinok (predvolene `rajce_fotky`) |
| `--png` | po stiahnutí prekonvertuje JPEG-y na PNG (vyžaduje `pip install pillow`) |
| `--thumbs` | stiahne náhľady namiesto originálov (rýchle, malé súbory) |

Už stiahnuté súbory sa preskakujú, takže sa dá spustiť opakovane a doťahovať
zvyšok.

## Poznámka k PNG

Fotky sú na Rajčeti uložené ako JPEG. Konverzia na PNG kvalitu nezlepší – iba
niekoľkonásobne zväčší súbory. Do telefónu je prakticky vždy lepšie nechať `.jpg`;
`--png` použi len ak PNG naozaj potrebuješ (napr. pre nejaký nástroj, ktorý iný
formát neberie).

## Ako to funguje

Stránka albumu obsahuje v JavaScripte premenné `storage` (základná URL úložiska)
a `photos` (zoznam súborov). Skript ich vyparsuje a originály sťahuje z
`<storage>/images/<súbor>`. Ak sa premenné nenájdu, použije sa záložné hľadanie
ciest `/images/…` a `/thumb/…` priamo v HTML. Zdieľacie odkazy tvaru
`/album/<hash>` fungujú tiež – skript drží cookies a nasleduje presmerovania.
