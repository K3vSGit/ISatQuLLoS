# ISatQuLLoS

Inter-Satellite Quantum Link Loss Simulations (ISatQuLLoS) is a Python/PyQt5 research application for estimating optical link losses in a two-satellite intersatellite communication network. The software focuses on diffraction-related losses and exports link-loss data that can be used with Satellite Quantum Modelling & Analysis Software (SatQuMa). For more information about SatQuMa, please visit the official page here: https://cnqo.phys.strath.ac.uk/research/quantum-information/satquma

The project was originally developed in 2023 for satellite quantum link-loss simulations. The graphical interface was redesigned and modernized in 2026.

## Features

- PyQt5 desktop interface for defining simulation parameters.
- Numerical link-loss simulations for a two-satellite network.
- Interactive Plotly/WebGL 3D orbital visualization.
- Animated satellite markers for visualizing orbital motion.
- Export of `Time-Loss.csv` for downstream compatibility with the SatQuMa software.
- Matplotlib plots for link-loss and system-loss analysis.

## Project Structure

```text
Main_Script.py      Application entry point and Qt high-DPI setup
Logic.py            Application logic, parameter handling, simulation flow
Ui_Design.py        Runtime UI layout, styling, Plotly/WebGL view helpers
ISatQuLLoS.py       Core simulation module
ICONS_rc.py         Qt resource bundle generated from interface assets
docs/               Build and packaging notes
```

Generated folders and files such as `build/`, `__pycache__/`, `.vs/`, `temp.html`, and `plotly.min.js` are intentionally excluded from version control. Runtime Plotly files are generated into the user's application-data folder when needed.

## Requirements (see requirements.txt)

- Python 3.10 or newer
- Windows is the primary tested platform
- PyQt5
- PyQtWebEngine
- NumPy
- SciPy
- Matplotlib
- Plotly

Install dependencies with:

```powershell
py -3 -m pip install -r requirements.txt
```

## Running From Source

From the project folder:

```powershell
py -3 Main_Script.py
```

Use the interface to:

1. Enter and confirm simulation parameters.
2. Select a valid output folder.
3. Run the link-loss simulations.
4. Use the generated `Time-Loss.csv` file with SatQuMa if needed.

## Windows Application Builds

See [docs/WINDOWS_BUILD.md](docs/WINDOWS_BUILD.md) for packaging notes. In short: a PyInstaller one-folder build is usually preferable to a single huge one-file executable for this kind of Qt/WebEngine scientific app.

## Research Software Notice

ISatQuLLoS is research software. Results depend on the selected assumptions, input parameters, and numerical resolution. Validate outputs independently before relying on them for design, publication, or operational decisions. For more context and information about assumptions and build, please see my bachelor thesis report complementing this software at URL: https://doi.org/10.5281/zenodo.20723274

## Copyright And License

Copyright (c) 2023-2026 Kevin Somenzi.

All rights reserved unless otherwise stated in the repository license or granted by prior written permission by the owner. ISatQuLLoS was originally developed in 2023 for satellite quantum link-loss simulations, with its graphical user interface developed in 2026. This software, including its source code, interface, design, documentation, and associated materials, is protected by copyright. Unauthorized copying, modification, redistribution, or use of this software outside the permissions granted by the applicable repository license or prior written permission from the owner is prohibited.

See [LICENSE](LICENSE) for the full project notice.

## Acknowledgements

With special thanks to Dr. Daniel Oi for his guidance, expertise, and constructive feedback.
