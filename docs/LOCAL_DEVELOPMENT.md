# Local Development Guide

This guide explains how to develop and test changes to the Dockrion framework itself.

## Building Agents with Local Dockrion Packages

When developing the Dockrion framework, you may want to test your changes by building agent images that use your local, unreleased version of Dockrion packages instead of the published PyPI versions.

### Prerequisites

1. **Build the unified Dockrion package:**
   ```bash
   cd /path/to/Dockrion
   make build
   ```
   This creates a wheel file in `dist/` (e.g., `dockrion-0.0.3-py3-none-any.whl`)

2. **Start the local PyPI server:**
   ```bash
   make pypi-local
   ```
   This starts a PyPI server on `http://localhost:8099` serving packages from the `dist/` directory.

   **Note:** Keep this terminal running while you build your agent images.

### Building with Local Packages

Use the `--use-local-dockrion-packages` flag when building your agent:

```bash
dockrion build --use-local-dockrion-packages
```

This flag:
- Installs the `dockrion` package from your local PyPI server (port 8099)
- Ensures your agent uses the latest local changes to Dockrion
- Is **hidden** in the CLI help (intended for framework developers only)

### Example Workflow

```bash
# 1. Make changes to Dockrion source code
vim packages/events/dockrion_events/context.py

# 2. Rebuild the unified package
make build

# 3. Start local PyPI server (if not already running)
make pypi-local

# 4. In another terminal, build your test agent
cd /path/to/your-agent
dockrion build --use-local-dockrion-packages

# 5. Test your agent
docker run -p 8080:8080 --env-file .env dockrion/your-agent:dev
```

### Configuration

**Custom PyPI Port:**
If port 8099 is already in use, you can specify a different port:

```bash
# Start PyPI server on custom port
DOCKRION_LOCAL_PYPI_PORT=9000 make pypi-local

# Build with custom port
DOCKRION_LOCAL_PYPI_PORT=9000 dockrion build --use-local-dockrion-packages
```

### Important Notes

1. **Normal builds are unaffected:** Without the `--use-local-dockrion-packages` flag, `dockrion build` uses packages from public PyPI as usual.

2. **Rebuild after changes:** Every time you modify Dockrion source code, you must:
   - Run `make build` to rebuild the package
   - Restart the PyPI server (or it will automatically pick up new files in `dist/`)
   - Rebuild your agent with `--use-local-dockrion-packages`

3. **Docker caching:** Use `--no-cache` if Docker is caching old package versions:
   ```bash
   dockrion build --use-local-dockrion-packages --no-cache
   ```

4. **Linux compatibility:** The flag uses `host.docker.internal` to access the host machine from Docker. This works on:
   - ✅ Docker Desktop (Mac/Windows)
   - ✅ Linux with Docker 20.10+ (automatically supported)
   - ❌ Older Linux Docker versions (may need manual configuration)

### Troubleshooting

**"Local PyPI server not running" error:**
- Ensure `make pypi-local` is running in another terminal
- Check the port is correct (default: 8099)
- Verify with: `curl http://localhost:8099/simple/dockrion/`

**Agent still uses old Dockrion version:**
- Rebuild the package: `make build`
- Check the wheel version in `dist/`: `ls -lh dist/`
- Use `--no-cache` flag to force fresh install

**Module not found errors:**
- Ensure all sub-packages are included in the unified build
- Check the wheel contents: `unzip -l dist/dockrion-*.whl | grep <module_name>`
- Verify `packages/dockrion/build_package.py` includes all packages

## Related Commands

- `make build` - Build the unified Dockrion package
- `make pypi-local` - Start local PyPI server
- `make clean` - Clean build artifacts
- `dockrion build --help` - Show all build options (note: `--use-local-dockrion-packages` is hidden)
