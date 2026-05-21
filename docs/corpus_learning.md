# Corpus learning léger

`corpus_learn` exploite les exports `mangatrad_review_blocks.csv` produits par `corpus_process`.

Il ne fait pas de fine-tuning lourd. Il construit un profil local transparent :

- tokens OCR suspects ;
- mots anglais/source recopiés dans la traduction ;
- candidats glossaire ;
- exemples à haut risque ;
- poids de risque par token à partir du corpus.

Commande :

```powershell
python -m cbz_manga_translator.corpus_learn `
  --analysis C:\temp\mangatrad_corpus_run_30_stratified\analysis `
  --out C:\temp\mangatrad_learned_profile
```

Fichiers générés :

```text
mangatrad_learned_profile.json
mangatrad_learned_report.md
mangatrad_project_glossary_seed.txt
mangatrad_qc_residue_words.txt
```

Le profil sert à décider quoi ajouter ensuite au dictionnaire, au QC et aux règles OCR. Il est volontairement lisible et modifiable à la main.
