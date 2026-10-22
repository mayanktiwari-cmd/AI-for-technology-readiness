# APCTT TRL - starter pipeline (v0.1, untested on real USGS PDFs)
1. `pip install openpyxl` (or use the kit's base env), then
   `python tools/download_pdfs.py /path/to/USGS_SDG_open_data_set_corrected.xlsx`  -> data/pdfs, data/labels.csv
2. `python eval/run_experiment.py --train-final` -> baselines vs ridge (leave-one-SDG-out), writes assets/trl_ridge.json
3. `participant_module/core.py` holds all logic; `adapter.py` must be aligned with the kit's MODULE_GUIDE.md / DATA_CONTRACT.md.
Quotes are always cut verbatim from extracted page text (no LLM generation).
