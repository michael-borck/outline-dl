# outline-dl

Download unit outline PDFs from Curtin University's LITEC system.

## Installation

```bash
pip install outline-dl
```

After installing, you need to install the browser binary:

```bash
playwright install chromium
```

### From source

```bash
git clone https://github.com/michael-borck/outline-dl.git
cd outline-dl
uv sync
uv run playwright install chromium
```

## Configuration

### Credentials

Credentials are resolved in this order:

1. CLI flags (`-u` / `-p`)
2. Environment variables (`UO_USERNAME` / `UO_PASSWORD`)
3. `.env` file (searched in order):
   - `~/.config/outline-dl/.env` (recommended for global installs)
   - `~/.outline-dl.env`
   - `./.env` (current directory)
4. Interactive prompt

To set up a `.env` file:

```bash
mkdir -p ~/.config/outline-dl
cat > ~/.config/outline-dl/.env <<EOF
UO_USERNAME=your_curtin_id
UO_PASSWORD=your_password
EOF
chmod 600 ~/.config/outline-dl/.env
```

### Unit codes

Unit codes (e.g. `COMP1000`) can be provided via:

1. **CLI arguments**: `outline-dl COMP1000 ISAD1000`
2. **File**: `outline-dl -f units.txt` (one per line, comma or space-separated)
3. **Interactive prompt**: enter a space or comma-separated list when prompted

## Usage

### Batch mode

When unit codes are provided on the CLI or via a file, the tool runs non-interactively — it automatically selects the latest version and the best matching availability.

```bash
# Download a single unit outline (defaults to Bentley Perth Campus)
outline-dl COMP1000

# Download multiple units
outline-dl COMP1000 ISAD1000 COMP2000

# From a file
outline-dl -f units.txt

# Specify a different campus
outline-dl -c "Singapore Campus" COMP1000

# Download for all campuses
outline-dl -c all COMP1000

# Custom output directory
outline-dl -o ~/Downloads COMP1000
```

### Interactive mode

When no unit codes are given on the CLI or via a file, the tool enters interactive mode. You'll be prompted for unit codes, then for each unit you can interactively select which version and availability to download.

```bash
outline-dl
```

### Skipping existing downloads

By default, PDFs that have already been downloaded are skipped. This makes it safe to re-run a batch after a crash — it will pick up where it left off.

To force re-download:

```bash
outline-dl --overwrite COMP1000
```

### Other options

```bash
# Watch the browser (useful for debugging)
outline-dl --visible COMP1000

# Adjust timeout for slow connections (milliseconds)
outline-dl --timeout 60000 COMP1000
```

PDFs are saved to `./outlines/` by default.

## Help

```
outline-dl --help
```

## License

MIT
