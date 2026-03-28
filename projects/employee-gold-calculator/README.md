# Employee Gold Calculator

Quick internal calculator for Saif Jewelers staff.

## What it does
- Takes a gram weight input
- Lets employee choose karat: 10K, 14K, 18K, 21K
- Returns your predetermined result from your private formula

## Edit your formula
Open `index.html` and update these sections:
- `FORMULA_CONFIG` values
- `calculateByYourFormula(grams, karat)` logic

## Run locally
Because this is a static file, there are 2 easy options:

1) Double click `index.html` and it opens in browser
2) Serve folder with Python:

```bash
cd "/Users/mothejeweler/Documents/AI Projects/Personal Assistant/projects/employee-gold-calculator"
python3 -m http.server 8080
```
Then open `http://localhost:8080`

## Share with employees
Fast options:
- Put this folder in a private internal drive (Google Drive/Dropbox/OneDrive)
- Host as a private webpage in your existing website or internal portal
- Deploy as static site (Netlify/Vercel/GitHub Pages) and share URL

If you want, this can be converted to a phone app next.
