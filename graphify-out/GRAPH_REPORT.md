# Graph Report - MangaTrad_v0_2_0  (2026-05-28)

## Corpus Check
- 127 files · ~77,800 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1656 nodes · 3975 edges · 110 communities (86 shown, 24 thin omitted)
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 1132 edges (avg confidence: 0.57)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a15abb50`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 97|Community 97]]
- [[_COMMUNITY_Community 98|Community 98]]
- [[_COMMUNITY_Community 99|Community 99]]
- [[_COMMUNITY_Community 100|Community 100]]
- [[_COMMUNITY_Community 101|Community 101]]
- [[_COMMUNITY_Community 102|Community 102]]
- [[_COMMUNITY_Community 104|Community 104]]
- [[_COMMUNITY_Community 107|Community 107]]
- [[_COMMUNITY_Community 108|Community 108]]
- [[_COMMUNITY_Community 109|Community 109]]

## God Nodes (most connected - your core abstractions)
1. `OcrBlock` - 231 edges
2. `ProjectCache` - 120 edges
3. `ProjectData` - 113 edges
4. `PageRecord` - 76 edges
5. `ArgosTranslator` - 75 edges
6. `EasyOcrEngine` - 52 edges
7. `TranslationQualityChecker` - 48 edges
8. `ReviewWindow` - 39 edges
9. `OcrFallbackEngine` - 38 edges
10. `EnglishDialogueNormalizer` - 38 edges

## Surprising Connections (you probably didn't know these)
- `test_default_refreshed_path()` --calls--> `default_refreshed_path()`  [INFERRED]
  tests/test_review_refresh.py → src/cbz_manga_translator/review_refresh.py
- `int` --uses--> `OcrBlock`  [INFERRED]
  tests/test_review_filter.py → src/cbz_manga_translator/core/models.py
- `OcrBlock` --uses--> `OcrBlock`  [INFERRED]
  tests/test_review_filter.py → src/cbz_manga_translator/core/models.py
- `str` --uses--> `OcrBlock`  [INFERRED]
  tests/test_review_filter.py → src/cbz_manga_translator/core/models.py
- `int` --uses--> `EasyOcrEngine`  [INFERRED]
  tests/test_easyocr_postprocess.py → src/cbz_manga_translator/ocr/easyocr_engine.py

## Communities (110 total, 24 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.05
Nodes (56): item_matches_filter(), _LazyQt, main(), PageImageView, _qt(), ReviewWindow, _QT_MAINWINDOW_BASE, _QT_WIDGET_BASE (+48 more)

### Community 1 - "Community 1"
Cohesion: 0.06
Nodes (76): build_volume_sources(), _candidate_page_indices(), _choose_busy_page_indices(), choose_page_indices(), _choose_stratified(), _choose_volumes(), CorpusSamplingResult, discover_series_groups() (+68 more)

### Community 2 - "Community 2"
Cohesion: 0.16
Nodes (30): EasyOcrEngine, bad_ocr_tokens(), from_dict(), OcrCandidate, word_tokens(), apply_common_ocr_corrections(), candidate_quality(), _dedupe_candidates() (+22 more)

### Community 3 - "Community 3"
Cohesion: 0.06
Nodes (59): Match, candidate_quality(), Repair ellipses when reviewed manga dialogue consistently implies them.      Thi, repair_probable_dialogue_ellipsis(), Repair OCR confusions typical of narrow all-caps manga lettering.      These are, Repair OCR confusions typical of narrow all-caps manga lettering.      These are, Repair OCR confusions typical of narrow all-caps manga lettering.      These are, repair_manga_font_confusions() (+51 more)

### Community 4 - "Community 4"
Cohesion: 0.09
Nodes (49): _block_sources(), build_ignore_memory(), canonical_ignore_key(), clear_ignore_memory_cache(), default_ignore_memory(), _default_memory_candidates(), IgnoreMemory, load_ignore_memory() (+41 more)

### Community 5 - "Community 5"
Cohesion: 0.11
Nodes (48): _bootstrap_basic(), _install_index_pairs(), main(), _print_pairs(), _test_translation(), Pattern, int, str (+40 more)

### Community 6 - "Community 6"
Cohesion: 0.08
Nodes (54): _build_manifest_from_pages(), CorpusManifestEntry, _count_images_under(), describe_corpus_path(), _entry_from_manifest_row(), _entry_group_key(), find_corpus_candidates(), _find_manifest_file() (+46 more)

### Community 7 - "Community 7"
Cohesion: 0.10
Nodes (51): CorpusProcessResult, Recognizer, BlockStats, page_block_stats(), ProjectCache, from_images(), OcrBlock, PageRecord (+43 more)

### Community 8 - "Community 8"
Cohesion: 0.09
Nodes (37): _block_row(), _corpus_path_labels(), export_review_dataset(), iter_review_rows(), Best-effort series/volume labels for exported corpus paths., build_learning_report(), _is_learnable(), LearningReport (+29 more)

### Community 9 - "Community 9"
Cohesion: 0.10
Nodes (40): apply_ocr_alternative(), _average_confidence(), _invalidate_generated_fields(), is_translation_protected(), merge_blocks(), _merged_alternatives(), move_block_order(), Merge selected blocks into the earliest block and remove the others.      Text i (+32 more)

### Community 10 - "Community 10"
Cohesion: 0.19
Nodes (34): _bbox_center(), _bbox_height(), _bbox_iou(), _bbox_min_overlap(), _bbox_union(), _bbox_width(), _can_merge(), _candidate_quality() (+26 more)

### Community 11 - "Community 11"
Cohesion: 0.13
Nodes (35): apply_review_pack(), _clean_cell(), create_review_pack(), _decision(), _detect_review_delimiter(), _find_block_index(), _normalized_series(), _prepare_review_row() (+27 more)

### Community 12 - "Community 12"
Cohesion: 0.10
Nodes (13): _CpuTranslation, _CudaFailTranslation, _FakeLanguage, _FakePackageEntry, _FakePackageModule, _FakeTranslateModule, object, str (+5 more)

### Community 13 - "Community 13"
Cohesion: 0.14
Nodes (29): main(), object, OcrBlock, Path, str, int, str, Path (+21 more)

### Community 14 - "Community 14"
Cohesion: 0.16
Nodes (32): Translator, default_refreshed_path(), _is_zone_fallback_candidate(), _iter_refreshable_blocks(), main(), _refresh_blocks_with_rules(), refresh_review_project(), _refresh_zone_ocr_alternatives() (+24 more)

### Community 15 - "Community 15"
Cohesion: 0.06
Nodes (31): 0.1.0, 0.1.4, 0.1.5, 0.1.6, 0.1.7, 0.1.8, 0.1.9, 0.2.0 (+23 more)

### Community 16 - "Community 16"
Cohesion: 0.16
Nodes (27): _compact(), has_probably_mixed_sfx(), is_probably_fused_source(), is_probably_incomplete_source(), is_probably_split_bubble(), is_probably_too_small_zone(), _words(), zone_issue_categories() (+19 more)

### Community 17 - "Community 17"
Cohesion: 0.18
Nodes (22): BaseHTTPRequestHandler, _as_bool(), _as_source_lang(), main(), preload_request(), Client-side request error for the local translation server., serve(), translate_blocks_request() (+14 more)

### Community 19 - "Community 19"
Cohesion: 0.15
Nodes (24): build_learned_profile(), _find_analysis_file(), _is_high_risk(), LearnedCorpusProfile, read_review_rows(), _risk(), _source_text(), _tokens() (+16 more)

### Community 20 - "Community 20"
Cohesion: 0.14
Nodes (36): _failure_page_indices(), main(), _parse_index_list(), EasyOcrEngine, Free OCR backend using EasyOCR.      EasyOCR returns polygons, text and confiden, Protocol, bbox_iou(), _best_match() (+28 more)

### Community 21 - "Community 21"
Cohesion: 0.17
Nodes (25): classify_block(), _compact(), diagnose_review_project(), DiagnosticItem, DiagnosticReport, _human_source(), _is_changed(), _letters_digits() (+17 more)

### Community 22 - "Community 22"
Cohesion: 0.17
Nodes (23): main(), build_ocr_memory(), canonical_ocr_key(), clear_ocr_memory_cache(), _default_memory_candidates(), default_ocr_memory(), _drops_strong_punctuation(), load_ocr_memory() (+15 more)

### Community 23 - "Community 23"
Cohesion: 0.17
Nodes (25): _changed_or_reviewed(), discover_review_projects(), evaluate_block(), _predict_source(), _predict_translation(), RegressionItem, RegressionReport, run_review_regression() (+17 more)

### Community 24 - "Community 24"
Cohesion: 0.08
Nodes (24): code:bash (mkdir -p graphify-out), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash (# Detect the correct Python interpreter (handles pipx, venv,), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c ") (+16 more)

### Community 25 - "Community 25"
Cohesion: 0.16
Nodes (14): RuntimeError, Any, bool, float, OcrBlock, SourceLang, str, test_local_server_url_is_normalized() (+6 more)

### Community 27 - "Community 27"
Cohesion: 0.10
Nodes (20): code:powershell (python -m cbz_manga_translator.corpus_process `), code:powershell (python -m cbz_manga_translator.corpus_process `), code:text (mangatrad_corpus_project.json), code:powershell (python -m cbz_manga_translator.corpus_process `), code:powershell (--limit-mode first), code:powershell (--limit-mode random --seed 47), code:powershell (python -m cbz_manga_translator.corpus_process `), code:text (pages/<serie>/<tome>/sample_xxx__page_yyyy.jpg) (+12 more)

### Community 28 - "Community 28"
Cohesion: 0.11
Nodes (18): Après extraction, code:text (\\192.168.1.30\sda1\lectures\mangas\romance\Serie A), code:text (D:\Mangas\SerieA\Tome 01.cbz), code:powershell (cd C:\temp\MangaTrad_v0_2_0), code:powershell (python -m cbz_manga_translator.corpus_sample `), code:text (mangatrad_corpus/), code:powershell (python -m cbz_manga_translator.corpus_process `), code:powershell (python -m cbz_manga_translator.corpus_process `) (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.25
Nodes (12): available(), _crop(), _extract_texts(), _lang_code(), Any, bool, float, int (+4 more)

### Community 30 - "Community 30"
Cohesion: 0.12
Nodes (16): code:block1 (/graphify                                             # full), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash (python3 -m graphify.watch INPUT_PATH --debounce 3), code:bash (graphify hook install    # install), code:bash (graphify claude install), code:bash (graphify claude uninstall  # remove the section), For --cluster-only (+8 more)

### Community 31 - "Community 31"
Cohesion: 0.13
Nodes (14): Branches recommandées, code:powershell (.\scripts\clean_repo.ps1), code:bash (./scripts/clean_repo.sh), code:powershell (git init), code:powershell (git remote add origin https://github.com/<USER>/<REPO>.git), code:text (main    version stable testée), code:powershell (git checkout -b dev), code:powershell (git tag v0.1.9) (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (14): 1. Générer un pack de correction, 2. Corriger le TSV, 3. Réinjecter les corrections, 4. Réexporter l'analyse et apprendre, code:text (mangatrad_human_review_pack.tsv), code:powershell (python -m cbz_manga_translator.corpus_review_pack `), code:text (mangatrad_human_review_pack.tsv), code:text (validate) (+6 more)

### Community 33 - "Community 33"
Cohesion: 0.13
Nodes (14): code:powershell (python -m cbz_manga_translator.argos_models --bootstrap-basi), code:powershell (python -m cbz_manga_translator.argos_models --install-index ), code:powershell (python -m cbz_manga_translator.argos_models --install C:\mod), code:powershell (python -m cbz_manga_translator.server --host 127.0.0.1 --por), code:powershell (python -m cbz_manga_translator.ocr_setup --commands), code:text (logs/mangatrad.log), Exécution locale, Logs (+6 more)

### Community 34 - "Community 34"
Cohesion: 0.13
Nodes (14): code:powershell (cd C:\temp\MangaTrad_v0_2_0), code:powershell (python -m cbz_manga_translator.ocr_setup --commands), code:powershell (winget install --id UB-Mannheim.TesseractOCR -e), code:powershell (.\.venv\Scripts\Activate.ps1), code:powershell (.\.venv\Scripts\Activate.ps1), code:powershell (python -m cbz_manga_translator.ocr_setup --check), code:powershell (python -m cbz_manga_translator.main), code:text (<dossier du projet>\logs\mangatrad.log) (+6 more)

### Community 36 - "Community 36"
Cohesion: 0.14
Nodes (13): Actions, Après review, code:powershell (python -m cbz_manga_translator.review_app C:\temp\mangatrad_), code:text (mangatrad_corpus_project.reviewed.json), code:powershell (python -m cbz_manga_translator.review_refresh `), code:powershell (python -m cbz_manga_translator.analysis_export `), Filtres et recherche, Lancement (+5 more)

### Community 37 - "Community 37"
Cohesion: 0.25
Nodes (10): DummyQualityChecker, DummyTranslator, DummyZoneFallback, Path, test_default_refreshed_path(), test_refresh_review_project_can_include_review_blocks(), test_refresh_review_project_collects_zone_ocr_alternatives_without_replacing(), test_refresh_review_project_preserves_human_reviewed_blocks() (+2 more)

### Community 38 - "Community 38"
Cohesion: 0.22
Nodes (9): poly(), int, test_append_supplemental_blocks_does_not_modify_existing_block(), test_postprocess_can_keep_unmerged_blocks_when_requested(), test_postprocess_filters_noise_and_merges_dialogue_lines(), test_postprocess_keeps_reviewed_sfx_labels_out_of_dialogue_merge(), test_postprocess_keeps_scribble_and_nod_sfx_out_of_dialogue_merge(), test_postprocess_keeps_sfx_labels_out_of_dialogue_merge() (+1 more)

### Community 39 - "Community 39"
Cohesion: 0.31
Nodes (12): collect_local_runtime_checks(), cuda_status(), format_runtime_checks(), package_status(), paddleocr_status(), Return non-network runtime diagnostics for the local/free execution policy., RuntimeCheck, tesseract_status() (+4 more)

### Community 40 - "Community 40"
Cohesion: 0.15
Nodes (12): 1. Lecture CBZ, 2. OCR primaire, 3. Fallback OCR, 4. Normalisation, 5. Traduction, 6. Quality check, 7. Correction humaine, code:text (CBZ) (+4 more)

### Community 41 - "Community 41"
Cohesion: 0.15
Nodes (13): code:block10 (You are a graphify extraction subagent. Read the files liste), code:bash ($(cat graphify-out/.graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:block8 (spawn_agent(agent_type="worker", message="Your task is to pe) (+5 more)

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (12): Apprentissage léger depuis corpus, code:text (Naru), code:powershell (.\.venv\Scripts\Activate.ps1), code:powershell (python -m cbz_manga_translator.corpus_learn `), code:powershell (python -m cbz_manga_translator.review_app C:\temp\mangatrad_), Corpus sans manifest, Docker, MangaTrad (+4 more)

### Community 43 - "Community 43"
Cohesion: 0.18
Nodes (10): run_gui(), default_log_dir(), logging_ready(), Configure application logging and native-crash faulthandler dumps.      Returns, setup_app_logging(), bool, Path, str (+2 more)

### Community 44 - "Community 44"
Cohesion: 0.18
Nodes (10): Apprentissage léger, code:text (mangatrad_review_blocks.csv), code:text (page_number), code:powershell (python -m cbz_manga_translator.analysis_export --project C:\), Commande CLI, CSV de revue, Export analyse / apprentissage léger, Fichiers exportés (+2 more)

### Community 45 - "Community 45"
Cohesion: 0.18
Nodes (10): code:text (ramen), code:text (Naru), code:text (NomPropre), Deux niveaux, Glossaire intégré, Glossaire projet, Pourquoi un glossaire, Prochaines améliorations (+2 more)

### Community 46 - "Community 46"
Cohesion: 0.18
Nodes (10): Backends, code:text (unhook → Inhook), Diagnostic, EasyOCR, manga-ocr futur, PaddleOCR optionnel, Prochaines améliorations OCR, Stratégie actuelle (+2 more)

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (9): Actions OCR, Décision 0.3.2 — interface à onglets, Décision V2.0, Filtres de blocs, Principe pour la suite, Problème, Recherche, Stratégie interface (+1 more)

### Community 48 - "Community 48"
Cohesion: 0.20
Nodes (9): Priorité actuelle, Roadmap, V0.3.x — Argos local, V2.1 — OCR comparable et sélectionnable, V2.1a — Export analyse et apprentissage léger, V2.2 — Traducteurs locaux interchangeables, V2.3 — Édition avancée des blocs, V2.4 — Overlay de traduction (+1 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (8): code:bash (docker build -t cbz-manga-translator-proto:local .), code:text (GUI Python Windows native), Commandes actuelles, Décision, Futur possible, Politique Docker, Pourquoi, Usages acceptés de Docker

### Community 50 - "Community 50"
Cohesion: 0.22
Nodes (8): Backend actuel, code:text (en -> fr), code:text (ya → you), code:text (Aww → Aww...), Contraintes, Limite assumée, Pré-traitement indispensable, Stratégie de traduction

### Community 52 - "Community 52"
Cohesion: 0.61
Nodes (7): default_path(), load(), load_or_create(), save(), Path, ProjectData, str

### Community 53 - "Community 53"
Cohesion: 0.25
Nodes (7): Architecture, code:text (src/cbz_manga_translator/), code:text (bbox), Modèle de bloc, Objectif, Organisation actuelle, Principes

### Community 55 - "Community 55"
Cohesion: 0.60
Nodes (3): from_dict(), Any, str

### Community 56 - "Community 56"
Cohesion: 0.33
Nodes (6): code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash (if [ ! -f graphify-out/.graphify_extract.json ]; then), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), For --update (incremental re-extraction)

### Community 57 - "Community 57"
Cohesion: 0.33
Nodes (6): code:text (ja -> fr), code:text (ja -> en -> fr), code:powershell (.\.venv\Scripts\Activate.ps1), code:powershell (python -m cbz_manga_translator.argos_models --install-index ), code:powershell (python -m cbz_manga_translator.argos_models --install C:\mod), Installer les modèles Argos localement

### Community 58 - "Community 58"
Cohesion: 0.53
Nodes (5): _check(), main(), _print_commands(), int, str

### Community 59 - "Community 59"
Cohesion: 0.50
Nodes (3): code:powershell (python -m cbz_manga_translator.corpus_learn `), code:text (mangatrad_learned_profile.json), Corpus learning léger

### Community 60 - "Community 60"
Cohesion: 0.50
Nodes (4): code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -m graphify save-result --question "), For /graphify query

### Community 61 - "Community 61"
Cohesion: 0.50
Nodes (4): code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -m graphify save-result --question "), For /graphify path

### Community 62 - "Community 62"
Cohesion: 0.50
Nodes (4): code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -c "), code:bash ($(cat .graphify_python) -m graphify save-result --question "), For /graphify explain

### Community 63 - "Community 63"
Cohesion: 0.50
Nodes (4): code:powershell (.\.venv\Scripts\Activate.ps1), code:powershell (.\.venv\Scripts\Activate.ps1), code:text (Modèle local : Serveur local HTTP), Serveur local Argos optionnel

### Community 64 - "Community 64"
Cohesion: 0.50
Nodes (4): code:text (logs/mangatrad.log), code:powershell (python -m cbz_manga_translator.ocr_setup --commands), code:powershell (python -m cbz_manga_translator.ocr_setup --check), Logs et diagnostic OCR

### Community 65 - "Community 65"
Cohesion: 0.50
Nodes (4): code:powershell (py -3.12 -m venv .venv), code:powershell (python -m cbz_manga_translator.main), code:powershell (python -m cbz_manga_translator.main --version), Installation Windows

### Community 66 - "Community 66"
Cohesion: 0.29
Nodes (10): BlockFilter, block_display_source(), block_matches_filter(), block_matches_search(), project_stats(), ProjectStats, visible_blocks(), bool (+2 more)

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (3): code:bash ($(cat .graphify_python) -c "), code:block27 (Graph complete. Outputs in PATH_TO_DIR/graphify-out/), Step 9 - Save manifest, update cost tracker, clean up, and report

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): code:bash ($(cat .graphify_python) -c "), code:block4 (Corpus: X files · ~Y words), Step 2 - Detect files

### Community 70 - "Community 70"
Cohesion: 0.67
Nodes (3): code:text (Argos Translate + packages locaux .argosmodel), code:text (en -> fr), Décision importante : plus de Hugging Face

### Community 71 - "Community 71"
Cohesion: 0.67
Nodes (3): code:powershell (python -m cbz_manga_translator.argos_models --list), code:powershell (python -m cbz_manga_translator.argos_models --test en "hello), Vérifier les modèles Argos installés

### Community 72 - "Community 72"
Cohesion: 0.67
Nodes (3): code:text (mangatrad_review_blocks.csv), code:powershell (python -m cbz_manga_translator.analysis_export --project C:\), Export analyse

### Community 73 - "Community 73"
Cohesion: 0.67
Nodes (3): code:powershell (python -m cbz_manga_translator.corpus_process `), code:powershell (--fallback suspects --include-optional-ocr), Traiter un corpus extrait

### Community 74 - "Community 74"
Cohesion: 0.67
Nodes (3): code:powershell (python -m cbz_manga_translator.corpus_review_pack `), code:powershell (python -m cbz_manga_translator.corpus_apply_review `), Correction humaine et apprentissage

### Community 75 - "Community 75"
Cohesion: 0.67
Nodes (3): code:text (D:\Mangas\Serie A), code:powershell (python -m cbz_manga_translator.corpus_sample `), Échantillonnage corpus

### Community 108 - "Community 108"
Cohesion: 0.27
Nodes (10): available(), _clean(), _lang_code(), _prepare_crop(), bool, int, OcrCandidate, Path (+2 more)

### Community 109 - "Community 109"
Cohesion: 0.60
Nodes (5): block(), test_block_display_source_prefers_normalized_then_corrected_then_raw(), test_page_and_project_stats(), test_search_matches_ocr_translation_and_warnings(), test_visible_blocks_filters_without_mutating_input_order()

## Knowledge Gaps
- **283 isolated node(s):** `PreToolUse`, `clean_repo.sh script`, `str`, `int`, `int` (+278 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `OcrBlock` connect `Community 7` to `Community 0`, `Community 1`, `Community 2`, `Community 4`, `Community 5`, `Community 6`, `Community 8`, `Community 9`, `Community 10`, `Community 11`, `Community 12`, `Community 13`, `Community 14`, `Community 16`, `Community 17`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 25`, `Community 37`, `Community 55`, `Community 66`?**
  _High betweenness centrality (0.260) - this node is a cross-community bridge._
- **Why does `normalize_ocr_text_for_translation()` connect `Community 3` to `Community 2`, `Community 10`, `Community 13`, `Community 22`, `Community 23`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **Why does `ProjectCache` connect `Community 7` to `Community 0`, `Community 1`, `Community 4`, `Community 37`, `Community 6`, `Community 8`, `Community 11`, `Community 13`, `Community 14`, `Community 20`, `Community 21`, `Community 22`, `Community 23`, `Community 52`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 228 inferred relationships involving `OcrBlock` (e.g. with `CorpusManifestEntry` and `CorpusProcessResult`) actually correct?**
  _`OcrBlock` has 228 INFERRED edges - model-reasoned connections that need verification._
- **Are the 119 inferred relationships involving `ProjectCache` (e.g. with `CorpusManifestEntry` and `CorpusProcessResult`) actually correct?**
  _`ProjectCache` has 119 INFERRED edges - model-reasoned connections that need verification._
- **Are the 110 inferred relationships involving `ProjectData` (e.g. with `CorpusManifestEntry` and `CorpusProcessResult`) actually correct?**
  _`ProjectData` has 110 INFERRED edges - model-reasoned connections that need verification._
- **Are the 72 inferred relationships involving `PageRecord` (e.g. with `CorpusManifestEntry` and `CorpusProcessResult`) actually correct?**
  _`PageRecord` has 72 INFERRED edges - model-reasoned connections that need verification._