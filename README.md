# anime-celify

## 1. 目的

`anime-celify` は、短尺のアニメ mp4 をローカル環境で処理し、寒色寄り・低〜中彩度・硬い影・青黒い線・選択的ハレーションを持つ 90 年代サイバーノワール系セル撮影感へ寄せるためのツールである。

初期版の主対象は `cyber_noir_95` プリセットであり、冷たく陰鬱な都市夜景、暗所、白色メカ、発光体を含むカットでの見え方を優先する。

## 2. 最初に必要な要件

- OS
  - macOS を確認済み
  - Linux はネイティブファイル選択に `zenity` を使用
  - Windows は PowerShell の標準ダイアログを使用
- Python
  - 3.11 以上
- 外部コマンド
  - `ffmpeg`
  - `ffprobe`
- 入力動画
  - `mp4` のみ
  - 15 秒以内
  - 24 fps / 30 fps を主対象
- 実行形態
  - 基本はローカル実行
  - 変換本体は OpenCV + FFmpeg + PySceneDetect による決定論的処理
  - 外部 AI API は必須ではない

## 3. 対応範囲

- 入力 mp4 を読み込み、出力 mp4 を生成する
- シーン検出に基づきカット単位で設定を切り替える
- `cyber_noir_95` を中心に、寒色寄りの中間調補正、彩度抑制、線の青黒化、暗部の締まり、選択的ハレーション、粒状感、時間方向の安定化を行う
- `--auto-tune` 指定時は、各カットを `urban_night` / `neutral_daylight` / `bio_mech_glow` に分類して差分パラメータを適用する
- 変換ログを JSON で保存する
- CLI 実行に加えて、ローカルファイル選択付きの `desktop` 実行を提供する

## 4. 非対応

- 長編動画の一括変換
- GUI 上での高度な編集
- 学習済み巨大モデルによる video-to-video 変換
- 固有作品の作画癖そのものの再現
- クラウド前提の処理
- 特定作品名をそのまま使ったプリセット名

## 5. インストール

### 5.1. 仮想環境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 5.2. FFmpeg 確認

```bash
ffmpeg -version
ffprobe -version
```

## 6. 初回確認手順

### 6.1. プリセット一覧

```bash
anime-celify presets list
```

### 6.2. 解析

```bash
anime-celify analyze input.mp4 --preset cyber_noir_95
```

### 6.3. 変換

```bash
anime-celify transform input.mp4 -o output.mp4 --preset cyber_noir_95 --auto-tune
```

### 6.4. ローカルファイル選択

```bash
anime-celify desktop
```

上記コマンドは、入力動画と出力先をネイティブダイアログで選択してから変換を実行する。対話を避けたい場合は次を使用する。

```bash
anime-celify desktop --input input.mp4 --output output.mp4 --preset cyber_noir_95
anime-celify-desktop
```

## 7. コマンド仕様

### 7.1. 変換

```bash
anime-celify transform input.mp4 -o output.mp4 --preset cyber_noir_95
anime-celify transform input.mp4 -o output.mp4 --preset cyber_noir_95 --auto-tune
anime-celify transform input.mp4 -o output.mp4 --config configs/custom.yaml
```

- `--preset` を省略し、`--config` も指定しない場合は `cyber_noir_95` を使用する
- 出力映像は H.264 / mp4 で再エンコードする
- 音声がある場合は可能な範囲で元の音声をコピーする

### 7.2. 解析

```bash
anime-celify analyze input.mp4 --preset cyber_noir_95
anime-celify analyze input.mp4 --preset cyber_noir_95 --output analysis.json
```

### 7.3. プリセット

```bash
anime-celify presets list
anime-celify presets show cyber_noir_95
```

### 7.4. デスクトップ実行

```bash
anime-celify desktop
anime-celify desktop --input input.mp4 --output output.mp4 --auto-tune
```

- macOS では `osascript` による標準ファイル選択ダイアログを使う
- Linux では `zenity` を使う
- Windows では PowerShell の標準ダイアログを使う

## 8. プリセット

内蔵プリセットは次の 3 つである。

- `cyber_noir_95`
- `tv_mecha_95`
- `sports_cel_warm`

初期版で最優先なのは `cyber_noir_95` である。主な処理方針は次のとおり。

- 中間調を青 / 青緑方向へ寄せる
- 彩度を抑える
- 線を pure black ではなく青黒寄りへ落とす
- 発光部と白色メカ周辺にのみ控えめな乳白ハレーションを加える
- 背景をやや柔らかくし、人物や主要線は残す
- カット単位で `urban_night` / `neutral_daylight` / `bio_mech_glow` を切り替える

## 9. AI / Auto-Tune の扱い

この OSS は、AI なしで動作する。初期状態では外部 API キーは不要であり、`--auto-tune` もローカルのヒューリスティック解析のみで動く。

現在の `--auto-tune` は次を行う。

- 代表フレームを抽出する
- 明るさ、彩度、寒色比率、ハイライト比率、肌色領域比率、字幕らしい領域などを計測する
- カットを `urban_night` / `neutral_daylight` / `bio_mech_glow` に分類する
- ベース preset に差分パラメータを加える

外部 AI を将来追加する場合の設計方針は次のとおり。

- 画像生成や描き直しには使わない
- Vision 対応 API を使う場合でも、返すのはカット分類と差分パラメータのみとする
- 変換本体は必ずローカルの決定論的パイプラインで実行する

## 10. 設定ファイル

プリセットは YAML で管理する。主要パラメータは次のとおり。

- `smoothing_strength`
- `edge_strength`
- `line_thickness`
- `line_blue_shift`
- `posterize_luma_levels`
- `posterize_chroma_levels`
- `saturation_scale`
- `contrast_scale`
- `gamma`
- `shadow_crush`
- `highlight_rolloff`
- `midtone_shift_r`
- `midtone_shift_g`
- `midtone_shift_b`
- `skin_desaturate`
- `skin_gray_shift`
- `halation_strength`
- `halation_radius`
- `emissive_mask_threshold`
- `grain_strength`
- `vignette_strength`
- `background_softness`
- `temporal_blend`
- `optical_flow_consistency`
- `subtitle_protect_enabled`

## 11. 出力ファイル

- 変換映像
  - `output.mp4`
- 実行ログ
  - `output.transform_log.json`

ログには次を記録する。

- `ffprobe` による入力情報
- シーン境界
- 各シーンで選ばれた shot profile
- 実際に使われた統合後パラメータ
- 実行時メモ

## 12. 画づくり上の到達点と限界

本ツールは、90 年代サイバーノワール系セル撮影感へ寄せることを目標にしているが、特定作品の作画や撮影処理を完全再現するものではない。

現時点で安定して狙っているのは次の要素である。

- 寒色寄りの中間調
- 低〜中彩度
- 深めの暗部
- 青黒寄りの線
- 発光部限定の控えめなにじみ
- 背景と前景の質感差

そのため、90 年代の攻殻機動隊方向の空気感へ寄せることは可能だが、作品固有の撮影設計、レイアウト、原画、背景美術、タイミングまで同一化することはできない。現在の実装は「方向性を安定して出す OSS」として扱うのが適切である。

## 13. 動作確認

このリポジトリでは次を確認済みである。

- `pytest` 通過
- `anime-celify transform ...` による mp4 生成
- `anime-celify analyze ...` によるカット分類出力
- `anime-celify desktop --input ... --output ...` によるローカル実行経路

ネイティブファイル選択ダイアログ自体は対話操作が必要なため、自動テストではダイアログの呼び出し先である変換処理を直接検証している。

## 14. テスト

```bash
pytest
```

smoke test では FFmpeg で短い mp4 を生成し、解析・変換・ログ出力までを確認する。

## 15. 既知の制限

- 15 秒を超える動画は受け付けない
- 入力は mp4 のみ
- 背景分離、字幕保護、カット分類はヒューリスティックである
- 実写や極端に派手なデジタルエフェクト主体の映像は対象外
- Linux のファイル選択には `zenity` が必要

## 16. ライセンス

MIT License
