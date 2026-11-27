# davidbird.org

Personal data portfolio, built with [Quarto](https://quarto.org) and hosted on Netlify.

## Layout

- `_quarto.yml`: site config
- `index.qmd`, `about.qmd`: landing and about pages
- `projects/`: one folder per project, each with its own `index.qmd`
- `src/`: reusable Python code used by the projects
- `sql/`: SQL scripts
- `data/`: `raw/` (gitignored), `interim/` (gitignored), `labels/` (committed hand-labelled samples)

## Build and publish

1. `pip install -r requirements.txt`
2. `quarto preview` while writing
3. `quarto render`, then commit `_site/` and push; Netlify serves the `_site` folder
   (Netlify > Project configuration > Build & deploy: publish directory `_site`, no build command)

Code cells run locally; `freeze: auto` stores the results so the site does not need the data to build.

## Data licences

Document the source and licence of every dataset in each project page.
