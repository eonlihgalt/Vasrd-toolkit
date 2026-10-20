# AGENTS.md

This file is the working plan for AI coding agents and contributors working on the VASRD Toolkit repository.

Purpose:
- Provide a concise but actionable project status.
- Define the highest-priority work needed to turn the repo into a reliable, usable MVP.
- Give future agents a clear sequence of tasks and expected outcomes.
- Serve as a living document that should be updated after major milestones.

Repository:
- https://github.com/eonlihgalt/Vasrd-toolkit

Project summary:
- The repo is a Python-based desktop toolkit for working with VASRD data from eCFR.
- It currently has a workable prototype structure: GUI, SQLite schema, and scraper logic.
- It is not yet production-ready or fully reproducible from a clean environment.

Current status:
- Overall completion: approximately 60-70% for an MVP demo
- Overall production readiness: approximately 30-45%
- Current repo state: working prototype / strong foundation, but still incomplete

Project assessment:
- Strengths:
  - Clear purpose and architecture.
  - SQLite schema exists and is coherent.
  - A scraper is implemented to fetch VASRD data from eCFR.
  - A Tkinter GUI exists for import/search/export functionality.
  - The repo includes a README and setup direction.
- Gaps:
  - Dependency management is not fully defined in the repo.
  - Build/test validation is absent.
  - Error handling and data quality validation are limited.
  - Packaging/distribution is incomplete.
  - The project is not yet robust enough for a production release.

Agent operating principles:
- Favor correctness over speed.
- Validate behavior on a clean Python environment before claiming completion.
- Prefer small, testable changes over large refactors.
- Keep this document updated after milestones or major decisions.
- Do not treat the repo as complete until validation, packaging, and build checks are passing.

Priority roadmap

P0 — Must have before release-quality MVP
1. Reproducible environment setup
   - Add/verify requirements.txt.
   - Add/verify requirements-dev.txt.
   - Confirm a clean venv install works.
   - Confirm import paths and runtime dependencies resolve correctly.

2. App startup and schema validation
   - Ensure main.py launches cleanly.
   - Ensure schema is created on a fresh database.
   - Verify DB integrity checks pass.

3. Import validation against real data
   - Test eCFR import with known dates.
   - Confirm counts and rows are inserted as expected.
   - Verify idempotency: import twice does not corrupt or duplicate data.

4. Data quality and integrity checks
   - Validate diagnostic codes, body systems, criteria rows, and notes.
   - Compare counts and expected section expectations.
   - Confirm search results are accurate.

5. Basic automated tests
   - Add schema smoke tests.
   - Add sample XML fixture tests for parsing.
   - Add export/search tests.
   - Add duplicate handling validation tests.

P1 — Should have for user-facing usability
1. Improve robustness of scraper
   - Handle edge-case XML structures.
   - Add better logging for import failures.
   - Improve retry and rate-limit handling.

2. Improve GUI reliability
   - Add clearer progress output.
   - Improve status messages and empty states.
   - Reduce brittle operations around reset and backup.

3. Add data export improvements
   - CSV is functional but should be validated.
   - Consider JSON export or report generation if useful.

4. Documentation improvements
   - Expand README with actual usage flow and expected behavior.
   - Document troubleshooting for rate limiting, setup issues, and import failures.

P2 — Nice to have / release polish
1. Packaging
   - Ensure a Windows executable can be built with PyInstaller.
   - Finalize installer packaging if needed.

2. CI/CD and quality gates
   - Add linting.
   - Add tests in CI.
   - Add a lightweight smoke build pipeline.

3. Release workflow
   - Versioning.
   - Changelog.
   - Release notes.

Feature-by-feature completion checklist

Core functionality
- [ ] App launches in a clean environment
- [ ] Database creates schema successfully
- [ ] eCFR import works with a valid date
- [ ] Search returns valid results
- [ ] Export CSV works reliably
- [ ] Reset/backup flows do not corrupt data
- [ ] Duplicate imports are safe

Quality and reliability
- [ ] Dependencies are defined and reproducible
- [ ] Real import is validated on sample data
- [ ] Error conditions are logged clearly
- [ ] Network failures and malformed XML are handled gracefully
- [ ] Tests exist for schema, parser, and export flows

Packaging and release
- [ ] README is complete and accurate
- [ ] Build instructions are verified
- [ ] PyInstaller/installer build succeeds
- [ ] Release notes exist
- [ ] CI smoke checks pass

Risk register

1. Data correctness risk
   - The scraper relies on parsing CFR XML with regex and section heuristics.
   - Risk: changes in CFR text formatting may produce incomplete or incorrect data.
   - Mitigation: add fixture-based tests and validation checks against known sample data.

2. Duplicate/integrity risk
   - Database insert logic may not fully guard against stale updates or duplicates.
   - Risk: imported data may be duplicated or inconsistent.
   - Mitigation: add idempotent import checks, integrity verification, and tests.

3. Environment reproducibility risk
   - The project may not be installable from a fresh environment without additional setup files.
   - Risk: future agents cannot reliably reproduce the build.
   - Mitigation: create and validate complete requirements files and install docs.

4. Packaging risk
   - Desktop packaging is not yet validated.
   - Risk: the application may not work as a released executable.
   - Mitigation: build and test the executable process with PyInstaller.

5. Quality assurance risk
   - There are no visible automated tests.
   - Risk: regressions are easy to miss.
   - Mitigation: add unit tests and CI smoke checks.

Recommended execution sequence for future agents

Stage 1: Environment and boot
- Verify dependencies and install path.
- Ensure the app starts from a clean Python environment.
- Confirm no import errors from package structure.

Stage 2: Data correctness and import
- Validate import with a known date.
- Confirm a realistic dataset is inserted.
- Check section mapping, rating criteria insertion, and notes parsing.

Stage 3: UI and workflow
- Validate the intended desktop workflow.
- Fix any brittle GUI behavior.
- Review backup/reset operations.

Stage 4: Packaging and release readiness
- Build the executable.
- Validate the app in a packaged environment.
- Improve README and release docs.

Stage 5: Hardening and automation
- Add tests.
- Add CI.
- Add release process documentation.

Milestone expectations

Milestone 1: reproducible install and startup
- Completed when a fresh venv can install dependencies and launch the app without import errors.

Milestone 2: import works reliably
- Completed when a known eCFR date imports into SQLite without errors, with verifiable counts.

Milestone 3: MVP usability
- Completed when the user can import, search, view details, and export data without manual debugging.

Milestone 4: release quality package
- Completed when the executable build works and the project is documented for end-user deployment.

Update policy for this document
- Update this file whenever a milestone is completed.
- Add a short status note under "Update log" when major changes happen.
- Keep this file as the canonical operational summary for the repo.

Update log
- Initial creation: 2026-10-20
- Status: project is an active prototype with targeted MVP completion plan

Suggested next actions for the next agent
- Confirm dependency files and install flow.
- Run a clean environment smoke test.
- Verify the app starts successfully.
- Validate an import using a known date.
- Fix any runtime blocking issues before moving to polish tasks.

This document should be treated as the current project brief and should be edited as work progresses.
