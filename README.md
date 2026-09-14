# tidemoon-data

気象庁の潮位表テキストを、Pebble ウォッチフェイス tidemoon 用の 1日1JSON に変換して GitHub Pages で配信するリポジトリ。

## セットアップ
1. このリポジトリを GitHub に push
2. Settings → Pages → Source: "Deploy from a branch", Branch: `main` / `/docs`
3. Actions → "update tide data" → Run workflow（初回は手動で。地点記号を指定）
4. `https://<user>.github.io/tidemoon-data/<地点>/2026-09-14.json` が開けば完了

## 地点記号
気象庁「潮位表」ページの地点一覧で確認（例: 小松島）。`STATION` 引数で指定。

## JSON 形式
```json
{"start":1757775600,"series":"1120,1105,...","extrema":"0:227,1:610,...",
 "hi":[["03:47",172]],"lo":[["10:10",78]]}
```
- `start`: その日0時(JST)の unix 秒
- `series`: 0時〜翌12時の毎時潮位 cm（+1000 オフセット、37個）
- `extrema`: `種別:start からの分数`（0=満潮, 1=干潮）
