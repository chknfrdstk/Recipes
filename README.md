# Recipes

A personal recipe collection in Markdown — 173 recipes, organised by protein, each with a photo. Photos are committed in the repo so they render in Forgejo.

Live site: https://chknfrdstk.github.io/Recipes/ — Forgejo is home, GitHub is the mirror.

## Sections

- [Beef](beef/) 🥩 — 23 recipes
- [Chicken](chicken/) 🍗 — 62 recipes
- [Pork](pork/) 🐷 — 8 recipes
- [Seafood](seafood/) 🦐 — 14 recipes
- [Soups](soups/) 🍲 — 43 recipes
- [Sides](sides/) 🥗 — 2 recipes
- [Sauce](sauce/) 🫙 — 11 recipes
- [No Meat](no-meat/) 🥦 — 7 recipes
- [Desserts](desserts/) 🍰 — 3 recipes

## How to navigate

- Every page has a sticky nav bar under the header (Home + all nine sections, current section highlighted), so you can jump between sections from any recipe page.
- The home page has a card for each section, plus a "Recently added" section for recipes added in the last 30 days.
- Each folder has its own `README.md` index — a photo card per recipe.

## Layout

- One `.md` file per recipe, in its protein folder: `beef/`, `chicken/`, `pork/`, `seafood/`, `soups/`, `sides/`, `sauce/`, `no-meat/`, `desserts/`.
- Each recipe's photo lives in the folder's `images/` as `<slug>.jpg` and is linked in the `.md` at 600px wide.
- The source is credited as the last line of each recipe file.

## Repo structure

```
Recipes/
├── CHANGELOG.md
├── README.md
├── _config.yml
├── index.md
├── scripts/
│ ├── aliases.json
│ └── build-search-index.py
├── _includes/
│ ├── head-custom.html
│ └── search-box.html
├── _layouts/
│ └── default.html
├── assets/
│ ├── css/
│ │ └── style.scss
│ ├── data/
│ │ └── recipes.json (generated)
│ ├── icons/
│ │ └── *.png (20 section favicons)
│ └── js/
│ └── search.js
├── beef/ (23 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── chicken/ (62 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── pork/ (8 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── seafood/ (14 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── soups/ (43 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── sides/ (2 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── sauce/ (11 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
├── no-meat/ (7 recipes)
│ ├── README.md
│ ├── images/
│ └── *.md
└── desserts/ (3 recipes)
    ├── README.md
    ├── images/
    └── *.md
```

## Adding a recipe

Add the `.md` file and its photo, add a photo card to the folder's `README.md` (in alphabetical order), bump the counts in the folder README and the home page, rebuild the search index with `python3 scripts/build-search-index.py`, and add a [CHANGELOG.md](CHANGELOG.md) entry in the same commit.

## Workflow

Short-lived branches: make the change, push, merge, delete, move on.

## Change history

See [CHANGELOG.md](CHANGELOG.md).
