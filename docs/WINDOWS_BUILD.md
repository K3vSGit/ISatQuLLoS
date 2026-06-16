# Windows Build Notes

ISatQuLLoS uses PyQt5, QtWebEngine, Plotly, Matplotlib, NumPy, and SciPy. Those dependencies are large, so a fully self-contained Windows build will also be large. The main packaging choice is whether you want one large executable or a normal application folder/installer.

## Recommended Path

Use a PyInstaller one-folder build, then wrap that folder in an installer such as Inno Setup, WiX Toolset, NSIS, or a ZIP release.

Why this is recommended:

- PyInstaller one-file mode has to unpack bundled dependencies at startup, which makes launch time slow for large Qt/WebEngine applications.
- PyInstaller one-folder mode keeps dependencies already extracted beside the executable, so startup is usually much faster.
- Users can still download a normal installer or ZIP; they do not need an IDE.

## Suggested Workflow

Create a clean virtual environment:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

Build a one-folder app:

```powershell
pyinstaller --clean --noconfirm --onedir --windowed --name ISatQuLLoS Main_Script.py
```

The result will be:

```text
dist/
  ISatQuLLoS/
    ISatQuLLoS.exe
    _internal/
    ...
```

Distribute the whole `dist/ISatQuLLoS` folder as a ZIP, or use an installer tool to install the folder under `Program Files` and create Start Menu/Desktop shortcuts.

## Alternative: Nuitka Standalone

Nuitka can compile Python applications and create standalone folders. It may improve startup behavior in some projects, but QtWebEngine applications still require many support files, so the final distribution will not be tiny.

A starting point:

```powershell
python -m pip install nuitka ordered-set zstandard
python -m nuitka --standalone --windows-disable-console --enable-plugin=pyqt5 --output-dir=dist Main_Script.py
```

Expect to iterate on included data files and Qt plugin handling.

## Notes

- Avoid PyInstaller `--onefile` for day-to-day releases of this app unless you specifically need a single executable and accept slower startup.
- The final folder size is expected to be large because QtWebEngine, SciPy, Matplotlib, and Plotly all bring substantial dependencies.
- Runtime Plotly wrapper files are written to the user's application-data folder, so the installed application folder does not need to be writable.
- Test the packaged app on a clean Windows machine or VM before publishing a release.
- Do not commit `build/`, `dist/`, `temp.html`, or generated caches to git.
