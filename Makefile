all:
	@echo 'Makefile targets: frontend-install, frontend-build, dev, dev-rollup, ui-smoke, clean'

# Install frontend deps (tries --no-bin-links fallback for Termux).
# We disable npm progress spinner and force CI mode to avoid interactive spinners on Termux/CI.
# Output is tee'd to logs/frontend-install.log so you can inspect the full log.
frontend-install:
	@sh scripts/frontend_install.sh

frontend-build:
	cd frontend && npm run build

# dev: start backend + frontend watcher in one command
dev:
	bash scripts/dev_rollup.sh

# dev-rollup: start backend + rollup watcher (Termux-friendly)
dev-rollup:
	bash scripts/dev_rollup.sh

ui-smoke:
	cd frontend && npm run smoke

# Enter the full build/test shell from Nix.
shell:
	nix develop

# Clean target (optional)
clean:
	rm -rf frontend/node_modules frontend/dist
	rm -f logs/frontend-install.log
