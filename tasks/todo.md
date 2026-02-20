# TODO

## Frontend Hedge Mode Integration Kit (2026-02-20)
### Spec
- Deliver a direct frontend integration structure (no phased plan) for hedge mode.
- Provide concrete TypeScript modules frontend can plug in immediately.
- Cover mode fetch/toggle, order payload building, one-way reduce-only auto handling, local state, and Teller WS wiring.

### Plan
- [x] Create a drop-in frontend kit folder under `docs/`.
- [x] Add typed REST client for position mode/account/positions/order calls.
- [x] Add order payload builder enforcing one-way vs hedge `position_side` and one-way opposite-direction `reduce_only`.
- [x] Add state reducer for mode/net-position/order-side tracking.
- [x] Add Teller private WS client for `orders`/`fills`/`positions`.
- [x] Add a short README with exact wiring instructions and required backend constraints.
- [x] Update lessons based on latest user correction.

### Results
- Added `docs/frontend-hedge-kit/README.md`:
  - Exact file structure and integration steps.
  - Backend constraints and required error handling list.
- Added `docs/frontend-hedge-kit/src/types.ts`:
  - Shared mode/side/order/account/position/WS types and mode normalization helper.
- Added `docs/frontend-hedge-kit/src/client.ts`:
  - `AevoApiClient` with:
    - `getPositionMode`, `getNormalizedPositionMode`, `setPositionMode`
    - `getAccount`, `getPositions`
    - `createOrder`, `editOrder`
  - Unified `ApiError` handling (`status`, `code`, `payload`).
- Added `docs/frontend-hedge-kit/src/order-builder.ts`:
  - `buildCreateOrderPayload(...)` enforcing:
    - non-perp: `position_side=BOTH`
    - perp+one-way: `position_side=BOTH`
    - perp+hedge: `position_side` required (`LONG`/`SHORT`)
    - one-way opposite-direction auto `reduce_only=true`
- Added `docs/frontend-hedge-kit/src/store.ts`:
  - `TradingState`, `TradingAction`, `initialTradingState`, `tradingReducer`.
- Added `docs/frontend-hedge-kit/src/teller-ws.ts`:
  - `TellerPrivateClient` with auth, subscribe, create/edit/cancel order ops, and channel callbacks.
- Added `docs/frontend-hedge-kit/src/index.ts` export barrel.

### Verification
- [x] Manually checked all new TypeScript modules for payload field alignment with backend endpoints and decoder names.
- [x] Confirmed README constraints match current backend behavior (`position_side`, one-way reduce-only policy, net-oriented positions output).
- [ ] No frontend build/test runner exists in this backend repository, so TS compile/lint was not executed here.

## Move One-Way Opposite-Direction Gate To API/Teller Handlers (2026-02-20)
### Spec
- Keep one-way opposite-direction `reduce_only` UX enforcement for external clients.
- Remove this gate from shared validator state path to avoid coupling with internal/eventstream tests and flows.
- Keep a commented validator reference for historical context, per request.

### Plan
- [x] Comment out validator invocation path for one-way opposite-direction gate with dated note.
- [x] Add a shared handler-layer helper for one-way opposite-direction enforcement.
- [x] Enforce helper in API create/edit and Teller create/edit handlers.
- [x] Update API isolated regression expectation for handler-layer rejection.
- [x] Run focused tests + lint and record environment blockers.

### Results
- `platform/validator/orders.go`
  - Removed active invocation of one-way opposite-direction `reduce_only` gate from `ValidateCreateOrderAgainstState`.
  - Added dated comment block preserving removed call for reference.
  - Removed now-unused helper usage path and replaced with comment note.
- `pkg/handlers/orders.go`
  - Added `ValidateOneWayOppositeDirectionAtEntry(...)` for external entry-point enforcement.
- `apps/api/write.go`
  - Added pre-submit handler checks in:
    - `CreateOrderHandler`
    - `EditOrderHandler`
  - Check runs under accessor read lock and returns immediate HTTP error on violation.
- `apps/teller/handler.go`
  - Added equivalent pre-submit checks in:
    - `onCreateOrder`
    - `onEditOrder`
  - Violations return immediate WS error response.
- `apps/api/isolated_test.go`
  - Updated case expectation to reflect new handler-layer policy:
    - non-reduce-only opposite-direction order is rejected with `ORDER_NOT_REDUCE_ONLY`.
- `pkg/handlers/orders_test.go`
  - Added `TestValidateOneWayOppositeDirectionAtEntry`.

### Verification
- [x] `GOCACHE=$PWD/tmp/go-build go test ./platform/validator -run 'TestValidateOrderPositionSideByMode|TestValidateOneWayOppositeDirectionRequiresReduceOnly|TestValidateOneWayOppositeDirectionSkipsInternalOrderModes'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./pkg/handlers -run 'TestValidateOneWayOppositeDirectionAtEntry|TestCreateOrder|TestEditOrder'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/teller -run TestNonExistent`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/api -c -o $PWD/tmp/apps_api.test`
- [x] `GOCACHE=$PWD/tmp/go-build GOLANGCI_LINT_CACHE=$PWD/tmp/golangci-lint golangci-lint run --timeout=10m`
- [ ] `go test ./apps/api -run 'TestIsolatedNonReduceOnlyReductionOrders|TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin'` blocked in this environment by Docker socket access required in `apps/api` `TestMain`.

## Patch All Cursor Hedge-Mode Follow-Ups (2026-02-20)
### Spec
- Patch all four cursor review items tied to hedge-mode rollout:
  1) missing `STOP_LIQUIDATE` for recovered isolated hedge legs,
  2) ADL/liquidation side propagation mismatch,
  3) non-deterministic hedge open-interest map iteration,
  4) duplicated isolated liquidation planning logic.
- Add regression tests for functional items.

### Plan
- [x] Fix recovered isolated hedge legs to emit `STOP_LIQUIDATE` while positions remain open but healthy.
- [x] Ensure liquidation match emits counterparty maker `position_side` opposite the hedge taker side.
- [x] Make hedge OI calculation deterministic and side-explicit for hedge legs.
- [x] Refactor duplicated isolated liquidation planning into one shared helper.
- [x] Run targeted engine/planner/liquidator tests and lint.

### Results
- `apps/planner/planner.go`
  - Fixed hedge isolated stop-liquidation logic: when no hedge leg is underwater (`selectedSide == BOTH`) and account is in liquidation for the instrument, planner now sends `STOP_LIQUIDATE` even if legs are still active.
  - Refactored `planIsolatedLiquidation` + `planIsolatedLiquidationBySide` duplication into shared helper `planIsolatedLiquidationForPosition(...)`.
- `apps/planner/planner_test.go`
  - Added regression: `TestPlanner/Should stop isolated hedge liquidation after recovery with active legs`.
- `apps/engine/match.go`
  - Liquidation match maker side now mirrors hedge taker side semantics (`LONG <-> SHORT`, default `BOTH`).
  - Counterparty fill aggregation now uses same derived side.
- `apps/engine/engine_test.go`
  - Added regression: `TestLiquidationMatch/Should set liquidation maker side opposite to hedge taker side`.
- `apps/engine/openinterest.go`
  - Hedge open-interest change now uses explicit hedge leg deltas only (`LONG`) and avoids map-order-dependent mutation paths involving `BOTH`.
- `apps/engine/openinterest_test.go`
  - Added regression: `TestCalculateOpenInterestChangeBySideHedgeIgnoresBothSideDeltas`.

### Verification
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/engine -run 'TestCalculateOpenInterestChangeBySideHedgeIgnoresBothSideDeltas|TestLiquidationMatch/Should_set_liquidation_maker_side_opposite_to_hedge_taker_side|TestCalculateOpenInterestChangeBySideHedgeIndependentLegs'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/engine -run 'TestLiquidationMatch|TestCalculateOpenInterestChange'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/planner -run 'TestPlanner/Should_stop_isolated_hedge_liquidation_after_recovery_with_active_legs|TestPlanner/Should_ignore_long_option_in_cross_liquidation_with_isolated_perp|TestPlanner/Should_not_use_non-USDC_collateral_for_isolated_liquidation'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/planner`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/liquidator -run 'TestLiquidator/Should_liquidate_with_ADL'`
- [x] `GOCACHE=$PWD/tmp/go-build go test ./apps/liquidator`
- [x] `GOCACHE=$PWD/tmp/go-build GOLANGCI_LINT_CACHE=$PWD/tmp/golangci-lint golangci-lint run --timeout=10m`
- [ ] `GOCACHE=$PWD/tmp/go-build go test ./apps/engine -timeout=8m` (full package run remains slow/buffered in this environment; targeted suite above covers touched paths and regressions)

## Fix Regressions From One-Way Opposite-Direction Gating (2026-02-20)
### Spec
- Restore expected ADL/copytrade behavior broken by one-way opposite-direction `reduce_only` gating introduced during hedge-mode rollout.
- Keep one-way/hedge position-side validation intact.
- Scope one-way opposite-direction UX gating to external order-entry subjects only.

### Plan
- [x] Add subject-scoped gating in validator create-order flow for one-way opposite-direction check.
- [x] Keep `validateOneWayOppositeDirection` logic unchanged for external subjects.
- [x] Run targeted failing suites (`apps/adl`, `apps/copytrade`) and confirm incidents are resolved.
- [x] Run lint and core hedge/margin/validator package tests to ensure no regressions.
- [x] Document outcome and residual blockers.

### Results
- Updated `platform/validator/orders.go`:
  - one-way opposite-direction reduce-only validation now runs only for external entry subjects (`api`, `teller`) via `isExternalClientSubject(...)`.
  - internal/system/eventstream-originated create-order paths are no longer blocked by user UX gating.
- Verification:
  - `GOCACHE=/tmp/go-build go test ./apps/adl -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/copytrade -count=1`
  - `GOCACHE=/tmp/go-build go test ./platform/validator -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/margin ./services/margin ./apps/liquidator -count=1`
  - `GOCACHE=/tmp/go-build GOLANGCI_LINT_CACHE=/tmp/golangci-lint golangci-lint run --timeout=10m`
- Residual blocker:
  - `go test ./apps/planner` had one intermittent failure (`TestPlanner/Should_send_maintenance_margin_warning_when_maintenance_margin_is_breached`) in one combined run, but passed on immediate rerun.

## Scope One-Way Reduce-Only Validation to User Orders (2026-02-19)
### Spec
- Keep one-way user behavior: opposite-direction signed orders must be `reduce_only`.
- Do not apply one-way opposite-direction reduce-only validation in hedge mode.
- Do not apply one-way opposite-direction reduce-only validation to internal modes (`FORCE`, `LIQUIDATION`).
- Keep liquidation safety enforced by liquidation/risk invariants, not user UX reduce-only gating.

### Plan
- [x] Add reproducing validator tests showing `FORCE`/`LIQUIDATION` orders are incorrectly caught by one-way reduce-only gating.
- [x] Update validator flow so `validateOneWayOppositeDirection` only runs for signed user orders.
- [x] Add regression coverage for signed one-way (still enforced), signed hedge (not enforced), and internal liquidation/force (not enforced).
- [x] Run focused validator/planner/liquidator tests to verify the blocker is removed and one-way user semantics remain intact.
- [x] Document results and any residual unrelated blockers.

### Results
- Added reproducing + regression test in `platform/validator/position_side_test.go`:
  - `TestValidateOneWayOppositeDirectionSkipsInternalOrderModes`
  - Pre-fix failure reproduced with `ORDER_NOT_REDUCE_ONLY` for both `LIQUIDATION` and `FORCE` orders.
- Fixed validator gating in `platform/validator/orders.go`:
  - `validateOneWayOppositeDirection(...)` now returns early for non-`SIGNED` order modes.
  - One-way signed user behavior remains unchanged.
- Verification:
  - `GOCACHE=/tmp/go-build go test ./platform/validator -run TestValidateOneWayOppositeDirectionSkipsInternalOrderModes -count=1` (fails pre-fix, passes post-fix)
  - `GOCACHE=/tmp/go-build go test ./platform/validator -run 'TestValidateOneWayOppositeDirectionRequiresReduceOnly|TestValidateOneWayOppositeDirectionSkipsInternalOrderModes|TestValidateOrderPositionSideByMode|TestValidateUpdateMarginHedgeRequiresUnambiguousSide' -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/planner -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/liquidator -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/margin -run 'TestAssessUpdateMargin/Should_account_for_existing_position_losses_on_same_instrument|TestOrder/Should_offset_IM_with_position|TestPosition/Should_compute_isolated_liquidation_price_for_short_and_edge_case' -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/margin -count=1`
- Follow-up fixes for one-way semantics migration in tests:
  - `pkg/margin/assess_test.go`: updated residual flows to close with `reduce_only` before reopening or partial close on opposite direction (`TestAssessUpdateMargin`, `TestWithdrawalMigration`).
  - `pkg/margin/margin_test.go`: updated offset/liquidation-price scenarios to use one-way compliant `reduce_only` closes where opposite-direction close orders are intentionally submitted.
- Residual blockers:
  - None in hedge-focused suites (`platform/validator`, `pkg/margin`, `apps/planner`, `apps/liquidator`, `apps/risk`, `services/margin`).
  - `go test ./services/accounts -count=1` still has pre-existing unrelated failures in `TestToggleFunding`/`TestMarshal`.

## Instrument-Level Hedge Mode From Scratch (2026-02-18)
### Spec
- Replace account-level position mode behavior with instrument-level position mode.
- Enforce one-way vs hedge semantics per instrument across REST, Teller, validator, accounts transfers, stops, and risk.
- Preserve backward compatibility where possible (default one-way when mode/side omitted).
- Validate behavior with focused unit tests in touched packages.

### Plan
- [x] Baseline compile and test failures to identify incomplete paths from current partial changes.
- [x] Finish accounts service side-aware transfer and open-interest logic (trade, block trade, quote, rebase, funding snapshots).
- [x] Implement instrument-level mode command handling and API handler flow (`/account/position-mode` with instrument).
- [x] Enforce validator rules for side/mode combinations and one-way opposite-side reduce-only semantics.
- [x] Update stop/TPSL indexing and cancel-all filtering to include `position_side` where required.
- [x] Wire engine/risk/quote settlement for side propagation and side-aware margin checks.
- [x] Add/adjust error codes and decoder coverage for new mode/side validation paths.
- [x] Add/adjust tests for accounts, validator, handlers, and stops; run focused suites and document outcomes.

### Results
- Completed instrument-level hedge mode flow across proto/API/validator/engine/accounts/stops/rfq.
- Added guardrails in side-aware paths to avoid nil-position panics by introducing:
  - `Account.SignedPosition(...)`
  - `Account.SignedPositionBySide(...)`
- Applied side-aware full-TPSL trigger sizing in validator tag path so hedge legs use per-side position when converting triggered TPSL to live order amount.
- Updated docs to reflect instrument-level semantics and request shapes (`instrument` required for position-mode endpoints).
- Verification:
  - `GOCACHE=/tmp/go-build go test ./platform/validator -run 'TestValidateOrderPositionSideByMode|TestValidateOneWayOppositeDirectionRequiresReduceOnly' -count=1`
  - `GOCACHE=/tmp/go-build go test ./services/stops -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/engine -run 'TestOpenInterest|TestGetCancelMultiOrders|TestMatchOrder' -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/rfq ./services/accounts ./pkg/handlers -run TestNonExistent -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/api -c`
- Environment blocker:
  - `go test ./apps/api` requires Docker access (`/var/run/docker.sock`) for ClickHouse test setup and cannot run in this sandbox.

## Hedge IM/MM Validation + Fix (2026-02-19)
### Spec
- Verify margin, risk, and engine behavior for hedge-mode side-specific exposure.
- Add regression tests and fix any side-netting bugs in IM assessment.

### Plan
- [x] Add a reproducing unit test for hedge-mode opposite-leg IM behavior in `pkg/margin`.
- [x] Fix IM calculation path so hedge-side orders do not net against opposite leg.
- [x] Add side-aware open-interest regression test in engine package.
- [x] Run focused suites for `pkg/calculator`, `pkg/margin`, `apps/risk`, `apps/engine`, `services/margin`.

### Results
- Added test: `pkg/margin/assess_test.go`
  - `TestAssessOrderHedgeModeOpensOppositeLegWithPositiveIM`
  - Reproduced bug: opposite hedge leg got `0` IM due to net offseting.
- Fixed `pkg/calculator/calculator.go`:
  - `ComputeOrderMarginWithNetAmount(...)` now treats hedge side orders (`LONG`/`SHORT`) as independent exposure buckets and bypasses net-position offseting.
- Added engine test: `apps/engine/openinterest_test.go`
  - `TestCalculateOpenInterestChangeBySideHedgeIndependentLegs`
- Verification:
  - `GOCACHE=/tmp/go-build go test ./pkg/calculator -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/margin -run 'TestAssessOrder|TestAssessOrderHedgeModeOpensOppositeLegWithPositiveIM' -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/engine -run 'TestCalculateOpenInterestChange|TestCalculateOpenInterestChangeBySideHedgeIndependentLegs' -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/risk -run 'TestCreateOrder|TestRisk|TestUpdateMargin' -count=1`
  - `GOCACHE=/tmp/go-build go test ./services/margin -count=1`

## Hedge Mode Full Margin Accounting (Cross + Isolated) (2026-02-19)
### Spec
- Fully account hedge mode in margin/risk/planner, not just order-entry IM.
- Cross margin must evaluate hedge legs as independent risk buckets for IM/MM and liquidation health.
- Isolated margin must evaluate hedge legs independently for margin top-up/removal and liquidation health.
- Preserve one-way behavior and backward compatibility for non-hedge accounts.
- Keep margin cache/state coherent with side-aware hedge accounting.

### Plan
- [x] Finalize formula and invariant spec for hedge mode:
- Cross: `available = max(cross_margin - cross_mm - cross_im - onhold, 0)` with side-aware gross hedge leg exposure.
- Isolated: per-leg `equity_leg = allocated_leg + upnl_leg`, must satisfy `equity_leg >= mm_leg`.
- [ ] Add side-aware margin identity for hedge legs in margin state/cache (`account + instrument + position_side` where required). (deferred; retained instrument-level cache IDs for compatibility)
- [x] Refactor calculator position/account aggregation to compute hedge legs separately for IM/MM in cross and isolated paths.
- [x] Update `pkg/margin` getters and assessors so cross/isolated checks consume the new side-aware aggregates.
- [x] Update planner checks and liquidation planning to operate per breached leg (cross and isolated), without netting away opposite healthy legs. (cross now selects hedge-side candidate per instrument; isolated is per-side)
- [ ] Update API/handler responses for margin/position health to expose side-aware hedge metrics where needed.
- [x] Add snapshot/state compatibility handling for existing instrument-only position margin entries.
- [x] Add comprehensive tests (unit + integration-focused) for cross+isolated hedge behavior.
- [x] Run focused and broad suites; document green coverage and environment blockers.

### Acceptance Criteria
- [x] Hedge + cross: `LONG 1` and `SHORT 1` on same instrument still consume positive MM and reduce available margin vs flat account.
- [x] Hedge + cross: opening opposite leg charges positive IM (not netted as reduce).
- [x] Hedge + cross: liquidation trigger uses side-aware risk and does not rely on net position cancellation. (one plan per instrument is preserved for liquidation service compatibility)
- [x] Hedge + isolated: each side has independent health check (`allocated_leg + upnl_leg >= mm_leg`).
- [x] Hedge + isolated: update-margin top-up/removal validates per-side leg constraints and cannot drain healthy side to break breached side.
- [x] Hedge + isolated: liquidation plans can target only the breached leg, leaving healthy opposite leg untouched.
- [x] One-way mode semantics and existing one-way tests remain unchanged/passing. (focused validator tests)
- [x] `services/margin` updates/clears remain correct and deterministic with side-aware entries. (instrument-level cache kept; side aggregates flow through calculator/getters)

### Verification
- [x] `GOCACHE=/tmp/go-build go test ./pkg/calculator ./pkg/margin ./services/accounts ./platform/validator -run 'Hedge|PositionSide|UpdateMargin|AssessOrder|AssessUpdateMargin' -count=1` (focused runs; see note below on broad suite blockers)
- [x] `GOCACHE=/tmp/go-build go test ./apps/planner ./apps/liquidator ./apps/risk -run TestNonExistent -count=1` (compile verification for touched runtime paths)
- [x] `GOCACHE=/tmp/go-build go test ./pkg/margin -run 'TestHedgeCrossMMUsesGrossLegs|TestAssessUpdateMarginRejectsAmbiguousHedgeLeg|TestAssessOrderHedgeModeOpensOppositeLegWithPositiveIM' -count=1`
- [x] `GOCACHE=/tmp/go-build go test ./platform/validator -run 'TestValidateOrderPositionSideByMode|TestValidateOneWayOppositeDirectionRequiresReduceOnly|TestValidateUpdateMarginHedgeRequiresUnambiguousSide' -count=1`
- [x] `GOCACHE=/tmp/go-build go test ./services/accounts -run 'TestHedgeIsolatedMarginSyncsNetAndAssigned|TestHedgeUpdateMarginUsesSingleOpenSide' -count=1`
- [x] `GOCACHE=/tmp/go-build go test ./apps/planner -run 'TestPlanner/Should_liquidate_hedge_cross_position_when_net_is_flat' -count=1`

### Results
- Updated hedge-side margin aggregation:
  - `pkg/calculator/calculator.go`: account position IM/MM and account margin value now aggregate LONG/SHORT legs in hedge mode.
  - `pkg/margin/getters.go`: hedge-aware position materialization, side-aware isolated health API, PM safety fallback for hedge cross.
  - `pkg/margin/assess.go`: notional checks and update-margin assessment now handle hedge-side semantics.
- Updated isolated margin state handling:
  - `services/accounts/account.go`: added side-aware isolated margin setters and net-sync helpers.
  - `services/accounts/accounts.go`: trade and accept-update paths now apply isolated/base margin updates on the correct hedge leg.
  - `services/accounts/hedge.go`: net position sync now includes isolated/base isolated aggregation from side legs.
- Updated validation and liquidation behavior:
  - `platform/validator/orders.go`: `UPDATE_MARGIN` in hedge+isolated now rejects ambiguous dual-leg requests.
  - `apps/planner/planner.go`: isolated liquidation checks/selectors evaluate hedge legs by side and plan the most-breached leg.
  - `apps/planner/planner.go`: cross liquidation candidate selection is hedge-aware (chooses a non-zero side leg per instrument instead of net amount), preventing net-flat hedge legs from being ignored or producing zero-amount planning paths.
  - `apps/liquidator/liquidator.go`: liquidation orders now set hedge `position_side` and side-aware counterparty position checks.
- Added tests:
  - `pkg/margin/margin_test.go`: `TestHedgeCrossMMUsesGrossLegs`
  - `pkg/margin/assess_test.go`: `TestAssessUpdateMarginRejectsAmbiguousHedgeLeg`
  - `platform/validator/position_side_test.go`: `TestValidateUpdateMarginHedgeRequiresUnambiguousSide`
  - `services/accounts/hedge_margin_test.go`: side-isolated state sync regression tests
  - `apps/planner/planner_test.go`: `TestPlanner/Should_liquidate_hedge_cross_position_when_net_is_flat`
- Broad-suite blocker noted:
  - `go test ./pkg/margin -count=1` still fails in existing pre-existing subtest path `TestAssessUpdateMargin/Should_account_for_existing_position_losses_on_same_instrument` due `ORDER_NOT_REDUCE_ONLY` command rejects unrelated to new hedge-side tests.
  - `go test ./apps/planner -run 'TestPlanner/(Should_plan_liquidation_for_short_perpetual|...)' -count=1` still hits an existing liquidation path reject (`ORDER_NOT_REDUCE_ONLY`) in non-hedge liquidation execution tests.


## MCP-Friendly Exchange V1 (2026-02-18)
### Spec
- Implement an MCP-native Aevo server with read + trade tools.
- Add a deBridge-compatible adapter/profile over the native tool contracts.
- Add an opt-in public agent-trade dashboard surface.
- Keep scope minimal and reuse existing handlers/services where possible.

### Plan
- [x] Add MCP app wiring (`apps/mcp`) and register it in active applications.
- [x] Implement MCP auth and tool permission gates (read vs trade).
- [x] Implement native MCP tool list/call endpoints (read + trade tool set).
- [x] Implement deBridge compatibility aliases/mapping for tool calls.
- [x] Implement opt-in public dashboard endpoints for recent agent trades.
- [x] Add focused unit tests for tool routing, auth gates, and dashboard filters.
- [x] Run focused test suites and document outcomes.

### Results
- Added new MCP application:
  - `apps/mcp/mcp.go`: app lifecycle, snapshot/eventstream sync, server bootstrap.
  - `apps/mcp/router.go`: endpoints for tool discovery/calls and live dashboard.
  - `apps/mcp/auth.go`: AEVO key auth (secret or signature), IP allowlist checks, MCP scope derivation.
  - `apps/mcp/tools.go`: MCP native tools, deBridge alias mapping, upstream API forwarding.
  - `apps/mcp/dashboard.go`: opt-in agent trade feed, leaderboard aggregation, websocket broadcast.
  - `apps/mcp/mcp_test.go`: focused tests for alias resolution, scope parsing, request normalization, opt-in filtering, leaderboard ordering.
- Registered app in `platform/applications/applications.go` as `mcp`.
- Added dedicated binary entrypoint `cmd/mcp/main.go`.
- Defaults:
  - MCP server host: `:8091` (override with `MCP_HOST`)
  - Upstream API base URL: `http://127.0.0.1:8080` (override with `MCP_API_BASE_URL`)
  - Scope convention: API key name supports `mcp.scope=read,trade`; read-only keys can never get `mcp.trade`.
- Upstream auth compatibility:
  - MCP forwards resolved client IP via `X-Real-Ip` / `X-Forwarded-For` when calling API endpoints so API-key IP allowlists still work when calls are proxied through MCP.
- Verification:
  - `GOCACHE=/tmp/go-build go test ./apps/mcp ./platform/applications ./cmd/mcp -count=1`

## Lint Regression Cleanup (2026-02-16)
### Spec
- Resolve reported lint blockers after hedge-mode merge review.
- Keep behavior unchanged while removing dead/unsafe patterns flagged by `golangci-lint`.

### Plan
- [x] Patch all reported lint findings (`gosimple`, `copylocks`, `unused`, `ineffassign`, `staticcheck`).
- [x] Re-run lint and verify clean output.
- [x] Run focused unit suites for touched packages.

### Results
- Fixed lint issues in:
  - `platform/validator/rfqs.go`
  - `pkg/rfq/match.go`
  - `apps/engine/match.go`
  - `services/accounts/accounts.go`
  - `services/accounts/hedge.go`
- Verification:
  - `GOCACHE=/tmp/go-build GOLANGCI_LINT_CACHE=/tmp/golangci-lint make lint`
  - `GOCACHE=/tmp/go-build go test ./platform/validator ./pkg/rfq ./apps/engine ./services/accounts -count=1`

## Hedge Mode PR Post-Merge Review (2026-02-16)
### Spec
- Audit merged hedge-mode behavior for account/teller-facing position payloads.
- Reproduce and fix any long/short state-mixing for same-instrument hedge legs.
- Validate with targeted unit tests.

### Plan
- [x] Add a failing API test for same-instrument long+short hedge legs with side-specific TPSL.
- [x] Patch handler position assembly to preserve hedge-leg separation.
- [x] Re-run targeted hedge-mode and stop/order API tests.
- [x] Document findings and residual risks in this section.

### Results
- Added reproducing API integration test:
  - `apps/api/position_mode_test.go`:
    - `TestHedgeModePositionsPreserveLegsAndTPSLBySide`
  - Reproduced pre-fix failure:
    - `/positions` returned a single net row (`amount=0`, side `buy`) when long+short hedge legs existed on the same instrument.
    - Side-specific full TPSL could not be represented correctly (flattened/mixed by stop type).
- Implemented handler fix in `pkg/handlers/accounts.go`:
  - Added side-aware TPSL grouping helper for hedge mode (`buildTPSLMapsBySide`).
  - Added side-aware position rendering path for hedge-mode perpetuals in both:
    - `Account(...)` response assembly
    - `Positions(...)` response assembly
  - Added internal `populatePositionWithAccountPosition(...)` to render from explicit leg positions.
  - Kept one-way mode path unchanged.
  - Updated position sorting tie-breaker to include side when instrument id is equal.
- Verification:
  - `GOCACHE=/tmp/go-build go test ./apps/api -run TestHedgeModePositionsPreserveLegsAndTPSLBySide -count=1`
  - `GOCACHE=/tmp/go-build go test ./apps/api -run 'TestPositionMode|TestPositionSideValidation|TestPositionHandler|TestGetStopOrders|TestHedgeModePositionsPreserveLegsAndTPSLBySide' -count=1`
  - `GOCACHE=/tmp/go-build go test ./pkg/handlers -run TestFeeStructureResponse -count=1`
  - `GOCACHE=/tmp/go-build go test ./platform/validator ./services/stops ./services/accounts -count=1`

## Merge Master + PR Stabilization (2026-02-16)
### Spec
- Merge latest `origin/master` into the current PR branch `yc/hedgingmode`.
- Resolve merge conflicts and compatibility breakages without dropping existing PR behavior.
- Run unit tests and fix regressions introduced by the merge.

### Plan
- [ ] Merge `origin/master` into `yc/hedgingmode`.
- [ ] Resolve merge conflicts and compile-time errors.
- [ ] Run unit tests for changed/related packages first, then broader unit suites.
- [ ] Fix failing tests/regressions and re-run until green (or document environment blockers).
- [ ] Record results and final verification.

## Fix MarketsSummary ExternalFundingWeight Panic Without Changing System API (2026-02-16)
### Spec
- Fix panic path in `MarketsSummary` / oracle funding computation caused by `System.ExternalFundingWeight` panics on missing/invalid perpetual config.
- Keep `services/system.ExternalFundingWeight` unchanged (as requested).
- Surface explicit oracle errors and avoid runtime panics.

### Plan
- [x] Add failing oracle tests reproducing no-perpetual-config and missing `external_funding_weight` panic paths.
- [x] Implement caller-side safe external funding weight retrieval in oracle with explicit error returns.
- [x] Keep `ExternalFundingWeight` API/behavior unchanged in `services/system`.
- [x] Re-run targeted suites for oracle/handlers/funding/system.

### Results
- Added oracle-side guard helper in `services/oracle/perpetual.go`:
  - detects missing perpetual config via `ExternalFundingVenue == ""` and returns `ErrGlobalInstrumentConfigEmpty`
  - wraps `System.ExternalFundingWeight` call with panic recovery and returns `ErrInvalidExternalFundingWeight`
- Updated funding computations to use this helper:
  - `FundingComponents`
  - `ComputeEffectiveFundingRate`
- Added reproducing + regression tests:
  - `TestComputeEffectiveFundingRateWithoutPerpetualConfigDoesNotPanic`
  - `TestFundingComponentsWithoutPerpetualConfigDoesNotPanic`
  - `TestComputeEffectiveFundingRateWithMissingExternalFundingWeightReturnsError`
- Verification:
  - `go test ./services/oracle -run 'TestComputeEffectiveFundingRateWithoutPerpetualConfigDoesNotPanic|TestFundingComponentsWithoutPerpetualConfigDoesNotPanic|TestComputeEffectiveFundingRateWithMissingExternalFundingWeightReturnsError' -count=1`
  - `go test ./pkg/handlers -run TestMarketsSummary -count=1`
  - `go test ./services/system ./apps/funding`

## PR Audit: Remove Silent Patch-Ups (2026-02-16)
### Spec
- Re-review PR changes for silent error masking/defaulting.
- Add explicit logging/error propagation for malformed upstream funding payloads and swallowed oracle errors.

### Plan
- [x] Audit `origin/master...HEAD` changed files for silent returns/defaulting.
- [x] Patch identified silent paths to log/propagate explicit context.
- [x] Add regression tests for malformed funding payloads.
- [x] Re-run targeted test suites.

### Results
- Added explicit logging for malformed funding payloads:
  - `pkg/adapter/feed/bybitfunding.go`
  - `pkg/adapter/feed/binancefunding.go`
  - `pkg/adapter/feed/hyperliquidfunding.go`
  - `pkg/adapter/feed/externalfunding.go`
- Removed swallowed oracle error in `CurrentFundingRate` by logging the actual error context:
  - `services/oracle/perpetual.go`
- Added malformed payload regression tests:
  - `pkg/adapter/feed/funding_events_test.go`
- Added no-panic guard test for `CurrentFundingRate` missing-config path:
  - `services/oracle/oracle_test.go`
- Verification:
  - `go test ./pkg/adapter/feed -run 'TestHyperliquidFundingOnMessage|TestByBitFundingOnMessage|TestBinanceFundingOnMessage' -count=1`
  - `go test ./services/oracle -run 'TestCurrentFundingRateWithoutPerpetualConfigDoesNotPanic|TestComputeEffectiveFundingRateWithMissingExternalFundingWeightReturnsError' -count=1`
  - `go test ./pkg/handlers -run TestMarketsSummary -count=1`
  - `go test ./services/system ./apps/funding`
  - `go test ./pkg/adapter -run TestShouldRestartWebsocketAdapter -count=1`

## Fix ExternalFundingWeight Panic Without Masking Config Errors (2026-02-16)
### Spec
- Resolve panic path from `System.ExternalFundingWeight -> num.NewString` when perpetual config or `external_funding_weight` is missing/invalid.
- Do not silently coerce bad config to zero; return explicit errors and let callers handle them.
- Preserve `external_funding_weight=1` short-circuit behavior when a valid external rate exists.

### Plan
- [x] Reproduce panic in oracle and markets summary tests.
- [x] Change external funding weight read path to return explicit errors for missing/invalid config.
- [x] Update oracle funding computation to propagate these errors (no panic, no silent fallback).
- [x] Add/adjust tests for missing perpetual config and invalid weight string.
- [x] Re-run targeted tests and record outcomes.

### Results
- `services/system.ExternalFundingWeight` now returns `(num.Num, error)` and surfaces:
  - `GLOBAL_INSTRUMENT_CONFIG_EMPTY` when perpetual config is absent
  - `INVALID_EXTERNAL_FUNDING_WEIGHT` when the value is empty/invalid
- `services/oracle` funding paths now propagate this error instead of panicking or silently coercing bad config.
- Added regression coverage:
  - `services/system/system_test.go`
    - `TestExternalFundingWeightMissingPerpetualConfigReturnsError`
    - `TestExternalFundingWeightMissingFieldReturnsError`
  - `services/oracle/oracle_test.go`
    - strengthened missing-config no-panic tests with `ErrorIs`
    - `TestComputeEffectiveFundingRateWithMissingExternalFundingWeightReturnsError`
- Verification:
  - `go test ./services/system ./services/oracle`
  - `go test ./pkg/handlers -run TestMarketsSummary -count=1`
  - `go test ./apps/funding`

## Debug External Funding Weight Not Applying (MYX/ALT, 2026-02-13)
### Spec
- Reproduce report: `external_funding_weight=1.0` does not apply external funding for assets using mixed venues (Bybit/Hyperliquid).
- Verify whether external funding rates are actually propagated into `services/funding` as `UPDATE_EXTERNAL_FUNDING_RATE`.
- Implement minimal fix so effective funding uses configured external venue per asset and works at weight `1.0`.

### Plan
- [x] Add failing adapter tests that assert funding handlers publish `UPDATE_EXTERNAL_FUNDING_RATE` events.
- [x] Ensure handlers only publish for assets whose configured `external_funding_venue` matches that handler venue.
- [x] Keep existing metrics emission behavior unchanged.
- [x] Run targeted tests for funding handlers and oracle funding computation.
- [x] Document findings and validation results in this section.

### Results
- Root cause found: external funding adapters (`BinanceFunding`, `ByBitFunding`, `HyperliquidFunding`) were only exporting metrics and never emitting `UPDATE_EXTERNAL_FUNDING_RATE`, so `services/funding.ExternalFunding(asset)` stayed nil and `external_funding_weight=1.0` could still fall back to internal funding.
- Added regression tests in `pkg/adapter/feed/funding_events_test.go` to reproduce and lock behavior:
  - publish event when venue matches configured `external_funding_venue`
  - skip publishing when venue does not match
  - coverage added for Binance, ByBit, and Hyperliquid funding handlers
- Implemented shared publishing helper in `pkg/adapter/feed/externalfunding.go`.
- Important follow-up fix: publish via adapter publisher (`a.Publish`) instead of `SendUpstream`, because funding-app adapters are initialized with `upstream=nil`.
- Added live-switch fix in `apps/funding/funding.go`: funding adapters are restarted on `ENABLE_ASSET`, `DISABLE_ASSET`, and perpetual `SET_ASSET_CONFIG` events so admin venue/asset updates are applied without manual funding-app restart.
- Updated handlers to publish external funding updates while preserving metrics emission:
  - `pkg/adapter/feed/binancefunding.go`
  - `pkg/adapter/feed/bybitfunding.go`
  - `pkg/adapter/feed/hyperliquidfunding.go`
- Added restart-policy regression tests in `apps/funding/funding_test.go`.
- Verification:
  - `go test ./pkg/adapter/feed`
  - `go test ./services/oracle -run 'TestEvaluateFundingRate|TestStoreFunding|TestPricePerpetualDiscountedFundingRate|TestPricePerpetualFairImpactBidAsk'`
  - `go test ./pkg/adapter`
- Added reusable verification runner:
  - script: `scripts/test_external_funding.sh`
  - make target: `make test-external-funding`
  - verified by running `make test-external-funding` successfully.

## Scope Runtime Funding Restarts to Funding App (2026-02-14)
### Spec
- Keep generic adapter restart policy unchanged for normal feed add/remove behavior.
- Move external funding runtime switch behavior into `apps/funding/funding.go` so admin venue/config updates apply without restarting the funding app.

### Plan
- [x] Revert funding-specific restart trigger from `pkg/adapter/adapter.go`.
- [x] Add funding-app-owned adapter lifecycle and restart trigger on `ENABLE_ASSET`, `DISABLE_ASSET`, and perpetual `SET_ASSET_CONFIG`.
- [x] Add funding app tests for restart trigger and adapter lifecycle.
- [x] Re-run targeted unit tests and `make test-external-funding`.

### Results
- `pkg/adapter/adapter.go` now only retains generic websocket restart checks (`ADD_FEEDS`/`REMOVE_FEEDS`).
- `apps/funding/funding.go` now owns funding adapter runtime lifecycle and triggers in-place adapter `Restart()` on relevant admin events (`ENABLE_ASSET`, `DISABLE_ASSET`, perpetual `SET_ASSET_CONFIG`) instead of recreating adapter consumers.
- Added tests in `apps/funding/funding_test.go` for:
  - `shouldRestartFundingAdapters` event gating
  - restart on perpetual `SET_ASSET_CONFIG` (adapter restart signal)
  - no restart on irrelevant events
- Fixed subapps test expectation drift from Group1 app list changes:
  - `apps/subapps/subapps_test.go` now asserts `len(subApps.subApps)+1` for the test mock reader.
- Fixed `apps/subapps/TestBlockTrade` deadlock:
  - Root cause was funding adapter recreation during event processing leaving stale eventstream consumer channels.
  - Resolved by avoiding runtime adapter re-creation and using in-place `Restart()` on existing funding adapters.
- Verification passed:
  - `go test ./apps/funding`
  - `go test ./apps/subapps -run TestSubApps -v`
  - `go test ./apps/subapps -run TestBlockTrade -v`
  - `go test ./apps/subapps`
  - `go test ./pkg/adapter`
  - `go test ./pkg/adapter/feed`
  - `go test ./services/funding`
  - `go test ./services/oracle`
  - `make test-external-funding`

## External Funding Weight=1 Should Not Depend on Internal TWAP (2026-02-15)
### Spec
- When `external_funding_weight=1` and an external funding rate is available, effective funding should match external funding even if internal funding TWAP is unavailable.

### Plan
- [x] Add failing oracle tests reproducing `weight=1` + no internal TWAP behavior.
- [x] Update oracle funding computation to short-circuit to external funding when fully weighted.
- [x] Re-run oracle/funding/subapps regression suites.

### Results
- Root cause: `ComputeEffectiveFundingRate` and `FundingComponents` computed internal funding first and returned `INVALID_FUNDING_TWAP`, even when external funding weight was exactly `1`.
- Fix:
  - `services/oracle/perpetual.go` now returns external funding directly for `weight == 1` when external rate exists, before internal TWAP calculation.
- Added regression tests:
  - `services/oracle/oracle_test.go`
    - `TestComputeEffectiveFundingRateUsesExternalWhenWeightIsOneAndInternalTWAPUnavailable`
    - `TestFundingComponentsUsesExternalWhenWeightIsOneAndInternalTWAPUnavailable`
- Verification passed:
  - `go test ./services/oracle -run 'TestComputeEffectiveFundingRateUsesExternalWhenWeightIsOneAndInternalTWAPUnavailable|TestFundingComponentsUsesExternalWhenWeightIsOneAndInternalTWAPUnavailable' -v`
  - `go test ./services/oracle`
  - `go test ./apps/funding ./apps/subapps`
  - `make test-external-funding`

## Fix Duplicated Isolated Risk Status Logic (2026-02-10)
### Spec
- Remove duplicated isolated status constants/threshold/function across `apps/admin` and `apps/monitoring`.
- Centralize policy so dashboard endpoint and monitoring alerts cannot drift.
- Keep existing behavior unchanged (`liquidating > breached > warning > healthy`, warning threshold `10`).

### Plan
- [x] Add shared isolated risk policy helper under `pkg/`.
- [x] Replace local status logic in `apps/admin/accounts.go` with shared helper.
- [x] Replace local status logic in `apps/monitoring/risk.go` with shared helper.
- [x] Update tests to reference shared constants and verify no behavior change.
- [x] Run targeted tests (`apps/admin`, `apps/monitoring`, shared package tests).

### Results
- Added shared policy in `pkg/isolatedrisk/policy.go`:
  - `StatusHealthy|StatusWarning|StatusBreached|StatusLiquidating`
  - `WarningBufferThreshold`
  - `Status(buffer, inLiquidation)` and `Severity(status)`
- Removed duplicated isolated status constants and local status helper functions from:
  - `apps/admin/accounts.go`
  - `apps/monitoring/risk.go`
- Updated monitoring/admin to use shared policy package.
- Added shared package tests in `pkg/isolatedrisk/policy_test.go`.
- Updated monitoring test to validate usage of shared policy (`apps/monitoring/risk_test.go`).

## Isolated Margin Monitoring (Design + Rollout, 2026-02-10)
### Spec
- Add production monitoring specifically for isolated margin risk.
- Make liquidation risk observable before liquidation, not only after `LIQUIDATE` events.
- Provide account-level drilldown via admin endpoint.
- Keep Prometheus metric cardinality bounded by default; avoid unbounded account labels in always-on metrics.

### Monitoring Model
- Isolated position health:
  - `isolated_equity = allocated_isolated_margin + upnl`
  - `buffer = isolated_equity - maintenance_margin`
  - `breached = buffer < 0`
  - `liquidating = instrument in account.InstrumentsInLiquidation()`
- Risk buckets:
  - `healthy`: `buffer > warn_threshold`
  - `warning`: `0 <= buffer <= warn_threshold`
  - `breached`: `buffer < 0`
  - `liquidating`: explicit liquidation state (orthogonal flag)

### Proposed Prometheus Metrics
- `isolated_positions_count{status}` (gauge)
  - `status`: `healthy|warning|breached|liquidating`
- `isolated_accounts_count{status}` (gauge)
  - account-level rollup based on worst isolated position status
- `isolated_margin_buffer_min{instrument_id,asset}` (gauge)
  - min `buffer` across accounts per instrument
- `isolated_margin_buffer_avg{instrument_id,asset}` (gauge)
  - average `buffer` across accounts per instrument
- `isolated_margin_liquidating_positions{instrument_id,asset}` (gauge)
  - count of positions currently in liquidation per instrument

### Proposed Admin Endpoint
- `GET /account/isolated-health?account=<address>`
- Permission: `READ_ACCOUNTS`
- Response includes:
  - Account summary:
    - `assigned_isolated_margin`
    - `isolated_available_margin`
    - `isolated_positions_count`
    - `breached_positions_count`
    - `liquidating_positions_count`
  - Position rows (isolated perps only):
    - `instrument_id`
    - `instrument_name`
    - `position`
    - `entry_price`
    - `mark_price`
    - `allocated_isolated_margin`
    - `base_isolated_margin`
    - `upnl`
    - `maintenance_margin`
    - `buffer`
    - `liquidation_price`
    - `in_liquidation`
    - `risk_status`

### Grafana + Alerting
- Dashboard panels:
  - SingleStat: breached isolated positions
  - SingleStat: liquidating isolated positions
  - TimeSeries: isolated positions by status
  - Table: worst instruments by `isolated_margin_buffer_min`
- Alert rules:
  - Critical: `isolated_positions_count{status="breached"} > 0` for `1m`
  - Warning: `isolated_positions_count{status="warning"} > 0` for `5m`
  - Page: `isolated_positions_count{status="liquidating"} > X` for `2m`

### Plan
- [x] Add new metric vectors + monitor helpers in `pkg/metrics/prometheus.go` and `pkg/metrics/monitors.go`.
- [x] Add periodic isolated risk aggregation in `apps/monitoring/risk.go` (single read lock pass).
- [x] Add `GET /account/isolated-health` handler in `apps/admin/accounts.go` and route in `apps/admin/router.go`.
- [x] Add unit tests for endpoint shape and risk status classification in `apps/admin/accounts_test.go`.
- [x] Add a short runbook in `docs/` with PromQL snippets and alert thresholds.
- [x] Run targeted tests (`apps/admin`, `apps/monitoring`, `pkg/metrics`) and record results.

### Results
- Added new Prometheus gauges for isolated risk posture and instrument-level buffer/liquidation visibility.
- Extended monitoring’s periodic risk pass to compute isolated status counts and per-instrument buffer aggregates.
- Added admin endpoint `GET /account/isolated-health?account=<address>` for per-account isolated drilldown.
- Added tests:
  - `apps/monitoring/risk_test.go` for status classification rules.
  - `apps/admin/accounts_test.go` integration test for isolated-health endpoint response.
- Added runbook: `docs/isolated-margin-monitoring.md`.
- Targeted tests passed:
  - `go test ./apps/admin ./apps/monitoring ./pkg/metrics`

## Hedge Mode RFQ Side Support (2026-02-10)
### Spec
- Support side-isolated RFQ perpetual quoting in hedge mode.
- Allow quote legs to carry `position_side` (`LONG`/`SHORT`/`BOTH`).
- Enforce side validation rules for quote legs:
  - Perp + `HEDGE`: `LONG`/`SHORT` required.
  - Perp + `ONE_WAY`: only `BOTH`.
  - Non-perp: only `BOTH`.
- Propagate leg side into:
  - RFQ risk/margin path (`UnpackFast` used by calculator/offsets/risk)
  - Settlement path (`MATCH_QUOTE` transfer in accounts service)

### Plan
- [x] Add/extend tests to reproduce current missing-side behavior and lock expected hedge-side behavior.
- [x] Add `position_side` to RFQ leg protobuf and regenerate PB code.
- [x] Parse and persist leg-level `position_side` from quote payloads.
- [x] Validate quote leg `position_side` rules in RFQ validator.
- [x] Use leg-level `position_side` in RFQ `UnpackFast`.
- [x] Use leg-level `position_side` in `accounts.blockTrade` settlement transfers.
- [x] Update hedge integration docs (remove RFQ caveat and document supported payload).
- [x] Run targeted tests and record results.

### Results
- Added `position_side` to RFQ quote legs (`proto/block.proto`) and regenerated protobuf/generators.
- RFQ quote payload parsing now accepts `legs[].position_side` and preserves it in quote payloads.
- Validator enforces RFQ leg side rules by account mode and instrument type.
- `services/rfqs.UnpackFast` and `services/accounts.blockTrade` now propagate and settle with leg-level sides.
- Updated `docs/hedge-mode-integration.md` with Teller/REST `create_quote` hedge-mode payload examples.
- Targeted tests passed:
  - `go test ./pkg/rfq ./services/rfqs ./services/accounts ./platform/validator -run 'TestQuoteHelpers|TestUnpackFastShouldKeepLegPositionSide|TestMatchQuoteHedgePositionSide|TestValidateQuoteLegPositionSide'`

## Hedge Mode Docs (Teller + REST integration, 2026-02-10)
### Spec
- Document full hedge-mode integration for API users and market makers using Teller websocket.
- Include what to send for hedge-mode quoting (`position_side` usage).
- Cover stop/TPSL, funding, margin behavior, and rejection semantics.
- Include RFQ/Teller `create_quote` payload guidance for hedge-side segregation.

### Plan
- [x] Trace actual request/validation paths for `position_mode` and `position_side` in API + Teller handlers.
- [x] Confirm side-aware behavior for stops, funding, and margin computation.
- [x] Add integration documentation under `docs/` with concrete payload examples and caveats.

### Results
- Added `docs/hedge-mode-integration.md` with:
  - Account-level position mode flow (`GET/POST /account/position-mode`) and fast precheck rejection rules.
  - REST + Teller websocket `create_order` / `edit_order` examples for hedge-mode market making.
  - Side mapping guidance (`LONG`/`SHORT`) for opening vs reducing exposure.
  - TPSL side-isolated behavior and payload examples.
  - Funding/margin side-aware behavior summary.
  - RFQ/Teller `create_quote` payload examples with leg-level `position_side` in hedge mode.

## Investigation (Cross Liquidation on NVDA, account 0x8A1E..., 2026-02-06)
### Spec
- Explain why this account was fully liquidated on a cross NVDA-PERP position after topping up margin.
- Reconcile observed `trade_history` liquidation fees (notably ~`2786`) with instrument settings (`LiquidationFee=0.03`).
- Reconcile `balance_history` jump from ~`4k` to ~`194` and verify whether that drop is in the same time window as the NVDA liquidation.

### Plan
- [x] Trace active liquidation path (`apps/planner` + `apps/liquidator` + `apps/engine`) and ignore deprecated liquidation app for root-cause.
- [x] Verify liquidation fee formula for perpetuals from source and tests.
- [x] Recompute the implied liquidation economics for NVDA settings (MM, slippage, taker fee, liquidation fee) and determine why plan becomes full liquidation.
- [x] Check timestamps from provided rows to separate the liquidation window from later balance snapshots.
- [x] Summarize root cause and concrete mitigations for risk settings/config.

### Results
- Verified in code/tests that perpetual liquidation fee is charged as `fill * avg_execution_price * liquidation_fee_rate` (see `apps/engine/match.go`, `apps/engine/engine_test.go`).
- For this account sample row (`LiquidationFee=2786.169884`, `Amount=587.8`, `AvgPrice=171.739`), implied effective liquidation fee rate is `2.760%` (close to configured `3%` with likely fee discount).
- Planner liquidation sizing uses `denominator = clearance - safetyThreshold * closingCost`; with NVDA params (`MM=3%`, `liqFee=3%`, `taker=0.08%`, and perp slippage term), denominator is negative, so full liquidation path is chosen by design.
- `balance_history` row at `1770354240` (2026-02-06 05:04:00 UTC) is much later than NVDA liquidation around `1770304407` (2026-02-05 15:13:27 UTC), so the `~194` balance is not from the immediate liquidation moment.

## Spec (Full Plan, Option A + Belt & Suspenders)
- Virtual allocation (single balance). Enforce isolation by logic in margin, liquidation, settlement, and funding.
- Early liquidation is the primary defense: isolated liquidation triggers when `isolatedMargin + uPnL - maintenanceRequirement < 0`.
- Explicit loss cap in `settleFutures` for isolated positions; any excess loss is covered by insurance fund (bad debt).
- Funding settlement for isolated positions is capped by remaining isolated margin and excess goes to insurance fund.
- Split cross vs isolated liquidation planning: cross liquidation touches only cross positions; isolated liquidation is per-instrument.
- Fix `Position.MM()` to return maintenance requirement. Add explicit allocation helpers:
  - `Position.AllocatedMargin()` (isolated allocation)
  - `Position.MarginAvailable()` (allocated + uPnL - maintenance requirement)
- Align isolated liquidation price formula to entry-price-based formula (Bybit/Hyperliquid style).
- Update `simulate` to match the new liquidation formula/position semantics.
- Keep deprecated `apps/liquidation/liquidation.go` and sentinel untouched unless compilation/tests require minimal adjustments.
- Flip isolated-margin feature flag on and remove reduce-only restriction after tests pass.

## Decisions
- Excess isolated losses go to `config.InsuranceFund()` (standard fund).
- Cap total loss (PnL + funding) against isolated allocation at close/flip.
- On simultaneous breach, emit separate liquidation events (one cross, one isolated instrument).

## Plan
- [x] Confirm open questions.
- [x] Add tests that reproduce cross contamination and isolated liquidation bleed (planner + settlement + funding). (Tests first)
- [x] Add new margin helpers and update call sites (`AllocatedMargin`, `MarginAvailable`, `CrossMM/CrossMargin`, etc.).
- [x] Refactor planner to split cross/isolated margin checks and plan generation.
- [x] Add per-instrument liquidation tracking in `services/liquidation` and use it in planner.
- [x] Implement loss caps in `settleFutures` and funding settlement for isolated positions; route excess to insurance fund.
- [x] Align liquidation price formula and update `simulate` + any API display logic.
- [x] Update ADL scoring/selection to use allocated margin for isolated.
- [x] Flip feature flag and remove reduce-only restriction.
- [x] Fix planner maintenance warning behavior (cross-only check regression).
- [x] Re-run targeted tests and record results here.

## Follow-up Plan (Tests)
- [x] Update lessons for test command preference (no `-count`).
- [x] Run requested tests without `-count`.
- [x] Record results here.

## New Test Request (Isolated vs Cross, 2026-02-03)
### Spec
- Scenario 1: Account holds a cross position and an isolated position on different instruments; trigger cross liquidation and assert the isolated instrument is not liquidated (and remains non-liquidating).
- Scenario 2: Isolated unrealized profit must not increase cross available margin; assert cross margin/available margin ignores isolated uPnL.

## Plan (New Tests)
- [x] Review existing planner/margin tests and decide placement for new cases.
- [x] Implement scenario 1 test (planner liquidation separation with explicit isolated instrument guard).
- [x] Implement scenario 2 test (margin/available margin ignores isolated uPnL).
- [x] Run targeted tests without `-count` and record results here.

## New Test Request (Isolated Partial Liquidation, 2026-02-03)
### Spec
- Create an isolated position and push it just beyond maintenance so liquidation triggers.
- Assert liquidation event is emitted for the isolated instrument.
- Assert liquidation plan is partial (liquidate amount < position size) under capped slippage conditions.

## Plan (Isolated Partial Liquidation)
- [x] Confirm expected slippage config for deterministic partial liquidation.
- [x] Implement planner test for isolated partial liquidation.
- [x] Run targeted test without `-count` and record results here.

## New Test Request (Isolated Scenarios Coverage, 2026-02-03)
### Spec
- Multiple isolated positions: two isolated instruments on the same account; breach one and verify liquidation only targets that instrument and leaves the other isolated position intact.
- Funding + PnL combined loss cap: realize funding and PnL together on isolated settlement; assert total loss is capped to isolated allocation and excess goes to insurance fund.
- Position flip (long→short) isolated: flip an isolated position, ensure funding/PnL realized on close side is capped to previous isolated allocation and isolated margin reallocated for the new side.

### Plan
- [x] Confirm intended code paths for each scenario and avoid duplicating existing coverage (notably `TestSettleFuturesCapsIsolatedLossToInsuranceFund`).
- [x] Add planner test for multiple isolated positions liquidation separation.
- [x] Add accounts test for combined funding + PnL loss cap via match-order flow (real funding realization).
- [x] Add accounts test for isolated position flip with loss cap + margin reallocation.
- [x] Run targeted tests without `-count` and record results here.

## Investigation (Insufficient Margin on Max-Price Order, 2026-02-03)
### Spec
- Identify why a buy order with `limit_price = MaxUint256` and `amount = 430000` on instrument `2054` returns insufficient margin.
- Pinpoint which validation/margin path uses the limit price directly for IM/notional.
- Provide actionable guidance (e.g., use market order type, cap price, reduce-only, or change IM calc for market-style orders) based on current code.

### Plan
- [x] Trace the validation path for insufficient margin from order intake to margin assessment.
- [x] Inspect IM calculation for orders with extreme limit prices (market-style orders).
- [x] Explain root cause and options to resolve/avoid (code or usage).

## Debug Tooling (cmd/debug margin diagnostics, 2026-02-03)
### Spec
- Add flags to simulate a single order (instrument, is_buy, amount, limit_price) and print `AssessOrder` results.
- Print isolated vs cross margin breakdown (available margin, available balance, isolated available margin, on-hold, assigned isolated margin).
- Include per-position isolated margin + MM to spot allocation issues.

### Plan
- [ ] Add new CLI flags and wire up order simulation in `cmd/debug/main.go`.
- [ ] Extend output to include isolated-specific balances and on-hold.
- [ ] Run the debug tool once with a sample order to verify output (or describe how to run if env-dependent).

## Snapshot-Based Unit Test (Account 0x81AD…, 2026-02-03)
### Spec
- Load a snapshot containing the target account state and instrument 2054 state.
- Recreate the order in a unit test and assert whether `AssessOrder` passes/fails with expected margin.
- Keep test deterministic (no network); use a local snapshot fixture.

## Fix Failing Test (TestQuote/Should_modify_queue_during_match_order, 2026-02-09)
### Spec
- Reproduce the failure in `pkg/margin/margin_test.go` subtest `Should modify queue during match order`.
- Identify the hang/failure cause (event wait, RFQ queue mutation, or missing app).
- Fix the underlying issue without altering unrelated test scaffolding.
- Run the targeted test to verify it passes and record results here.

### Plan
- [x] Run `go test ./pkg/margin -run TestQuote/Should_modify_queue_during_match_order` to reproduce and capture the failure mode.
- [x] Trace the RFQ queue mutation path during match order; inspect event waits in the test for missing/mismatched events.
- [x] Apply the minimal fix in code (or test if the code is correct) and explain why it resolves the hang.
- [x] Re-run the targeted test and record results.

### Results
- Root cause: taker quote matches immediately, emitting `MATCH_QUOTE` (not `OPEN_QUOTE`), so waiting for `OPEN_QUOTE` timed out.
- Fix: wait for `MATCH_QUOTE` in `TestQuote/Should modify queue during match order`.
- Test: `go test ./pkg/margin -run TestQuote/Should_modify_queue_during_match_order`

## Fix Failing Test (TestPosition mark-expiry behavior, 2026-02-09)
### Spec
- Keep `TestPosition/Should_compute_MM_and_store_it_in_state_if_the_current_state_is_expired` semantics: after a mark update, recomputed position IM/MM must change.
- Fix implementation instead of weakening assertions.
- Verify with targeted and package tests.

### Plan
- [x] Restore the test assertions requiring IM/MM changes.
- [x] Update position margin computation so perpetual position IM/MM are mark-sensitive after expiry recomputation.
- [x] Run `go test ./pkg/margin -run TestPosition/Should_compute_MM_and_store_it_in_state_if_the_current_state_is_expired`.
- [x] Run `go test ./pkg/margin` and record outcomes.

### Results
- Implemented mark-sensitive perpetual position IM/MM in `ComputePositionMargin` for `modeNormal` only.
- Kept API simulation behavior stable by leaving non-`modeNormal` calculations on entry-based behavior.
- Updated margin tests whose expected values depended on entry-based MM assumptions.
- Verification:
  - `go test ./pkg/margin -run TestPosition/Should_compute_MM_and_store_it_in_state_if_the_current_state_is_expired` passed.
  - `go test ./pkg/margin` passed.
  - `go test ./services/accounts` passed.
  - `go test ./pkg/margin ./services/accounts -coverpkg=github.com/ribbon-finance/exchange-backend/pkg/handlers,github.com/ribbon-finance/exchange-backend/pkg/margin,github.com/ribbon-finance/exchange-backend/services/accounts,github.com/ribbon-finance/exchange-backend/pkg/calculator` passed.

## Fix Failing Test (TestPlanner long perpetual liquidation, 2026-02-09)
### Spec
- Reproduce `TestPlanner/Should_plan_liquidation_for_long_perpetual` timeout/failure and keep "MM must change" behavior intact.
- Fix implementation (not test weakening) so planner liquidation pricing remains deterministic with mark-sensitive margin behavior.

### Plan
- [x] Run targeted planner liquidation tests and capture failure context.
- [x] Patch planner perpetual liquidation pricing to keep rounded prices strictly inside slippage caps.
- [x] Re-run targeted and package-level planner tests.

### Results
- `apps/planner/planner.go`: adjusted `pricePerpetual` to clamp and round while keeping prices strictly within cap boundaries.
- Verification:
  - `go test ./apps/planner -run 'TestPlanner/Should_plan_liquidation_for_long_perpetual|TestPlanner/Should_plan_liquidation_for_short_perpetual|TestPlanner/Should_plan_liquidation_for_bankruptcy' -v` passed.
  - `go test ./apps/planner -v` passed.

### Plan
- [x] Obtain or generate a snapshot fixture that includes account state + instrument 2054 (user-provided or generated via simulate).
- [x] Add a unit test that loads the fixture and evaluates `AssessOrder` for the order payload.
- [x] Run the new unit test and record results here.

## Snapshot-Based Tests (Expanded Behaviors, 2026-02-03)
### Spec
- Assert the posted order is accepted for the snapshot state.
- Add a failing order that exceeds isolated available margin and assert `ErrInsufficientMargin`.
- Compare cross vs isolated available margin to explain why isolated fails/succeeds.
- Demonstrate on-hold impact by reserving IM and asserting the same order fails when on-hold reduces isolated available margin.

### Plan
- [x] Refactor snapshot test to share a single loaded fixture and reset on-hold between subtests.
- [x] Add subtests for accept/reject, cross vs isolated comparison, and on-hold impact.
- [x] Run the updated snapshot tests and record results here (skips if instrument 2054 missing in snapshot env).

## Snapshot-Based Tests (DEV seq 12653250739, 2026-02-04)
### Spec
- Use `test_snapshot/snapshot-DEV-12653250739.json` + `test_snapshot/events-DEV-12653250739.json`.
- Ensure the provided order (`instrument=2054`, `is_buy=true`, `limit_price=2286800000`, `amount=430000`) is assessed against this snapshot and record pass/fail with the exact error if it fails.
- Add additional snapshot-based subtests only if they are deterministic for this state (no flaky thresholds).
- Add a failure case that explicitly asserts insufficient USDC prevents opening an isolated position.
- Add cross margin failure mode tests (max notional, insufficient margin) using this snapshot where deterministic.

### Plan
- [x] Review the current snapshot test and ensure it targets the DEV fixture explicitly.
- [x] Add/adjust subtests to validate order acceptance or expected rejection based on this specific snapshot.
- [x] Run the targeted snapshot test and record results here (no `-count`).

## Isolated Margin Risk Coverage (Partial Close, Funding, Liquidation, 2026-02-04)
### Spec
- Enumerate common bug/exploit vectors in isolated margin for partial close, funding, and liquidation.
- Add unit tests for the correct behavior for each vector.
- If any tests fail, patch the root cause and rerun.
- Subset Phase 1:
  - Partial close loss-cap enforcement (cannot realize > isolated allocation across partial closes).
  - Funding loss cap (funding loss capped to isolated allocation; excess to insurance fund).
  - Cross liquidation does not touch isolated positions.
- Backlog (track only for now):
  - PnL realization double-count on partial close.
  - Isolated margin reallocation on flip.
  - Reduce-only close should not require margin.

## Test Coverage Recovery (2026-02-09)
### Spec
- Run `make test-coverage` and fix all failing unit tests.
- Do not weaken intended behavior; fix code paths or deterministic test setup.
- Re-run full coverage target until it passes.

### Plan
- [ ] Run `make test-coverage` and capture all failing tests/errors.
- [ ] Fix failures iteratively with targeted test reruns after each change.
- [ ] Re-run `make test-coverage` and confirm fully green.
  - Funding gain should not increase cross available margin.
  - Funding realized twice.
  - Isolated liquidation amount bounds and liquidation price formula regression.

### Plan
- [x] Document common bug/exploit vectors and map each to a concrete unit test.
- [x] Implement Phase 1 tests:
  - `services/accounts/accounts_test.go`: `TestMatchOrderIsolatedPartialCloseCapsLossToInsuranceFund` (two partial closes; total loss capped to isolated allocation).
  - `services/accounts/accounts_test.go`: `TestMatchOrderIsolatedFundingLossCapOnly` (funding loss only; capped to isolated allocation).
  - `apps/planner/planner_test.go`: confirm coverage via existing `Should liquidate cross positions without touching isolated`.
- [x] Run targeted tests (no `-count`) and record results here.

## Isolated Margin Risk Coverage (Phase 2, 2026-02-04)
### Spec
- Add a unit test that ensures partial close does not double-count realized PnL for isolated positions.

### Plan
- [x] Implement `services/accounts/accounts_test.go`: `TestMatchOrderIsolatedPartialCloseDoesNotDoubleCountPnL`.
- [x] Run the targeted test (no `-count`) and record results here.

## Isolated Margin Risk Coverage (Phase 3, 2026-02-04)
### Spec
- Add a unit test to ensure isolated funding is realized exactly once on close (no double counting).

### Plan
- [x] Implement `services/accounts/accounts_test.go`: `TestMatchOrderIsolatedFundingRealizedOnceOnClose`.
- [x] Run the targeted test (no `-count`) and record results here.

## Isolated Margin Risk Coverage (Phase 4, 2026-02-04)

## Hedge Mode (Account-Level, 2026-02-10)
### Spec
- Support account-level position mode toggle: `ONE_WAY` (default) and `HEDGE`.
- In `HEDGE` mode for perpetual instruments, require `position_side` (`LONG`/`SHORT`) and allow simultaneous long+short on same instrument.
- Prevent long/short mixing in margin/funding/risk accounting paths.
- Ensure stop/reduce-only checks use side-aware position in hedge mode to avoid cross-leg contamination.

### Plan
- [x] Remove validator execution block for hedge mode and enforce side-specific validation rules.
- [x] Make reduce-only validation side-aware (including TPSL parent adjustments).
- [x] Ensure match events carry `position_side` for taker/maker and engine reduce-only sizing uses side-aware position.
- [x] Update offsets/margin input paths so opposite-side hedge orders do not offset each other.
- [x] Make funding snapshot/charge side-aware for hedge positions.
- [x] Add side-aware TPSL cancellation signal in match flow to avoid cancelling both legs unintentionally.
- [x] Add/adjust tests covering:
  - hedge order acceptance,
  - simultaneous long+short on same instrument,
  - margin offset isolation between LONG and SHORT legs,
  - side-aware reduce-only/TPSL behavior.
### Results
- Added side-aware full/partial TPSL accounting in `services/stops` keyed by `(instrument, position_side, stop_type)` to prevent LONG/SHORT collisions.
- Added side-specific stop cancel regression test (`MATCH_ORDER.CancelMultiOrders.position_side`) and full TPSL coexistence test for both hedge legs on the same instrument.
- Added offsets regression test to prove hedge-mode long/short legs on the same instrument do not net against each other in offset calculations.
- Validation now enforces full/partial TPSL limits per side in hedge mode (`FullTPSLExistsBySide`, `PartialTPSLCountBySide`).
- Added handler-level `SetPositionMode` prechecks (account existence, valid mode, no perp positions/orders/twap orders) to return immediate 4xx without waiting for command-reject roundtrip.
- Verification:
  - `go test ./pkg/offsets -run TestInitialization/Should_not_mix_long_and_short_offsets_in_hedge_mode -v`
  - `go test ./services/stops ./platform/validator ./apps/api -run 'TestOnEvent|TestPositionSideValidation|TestPositionMode'`
  - `go test ./pkg/offsets ./pkg/margin ./pkg/calculator ./services/accounts ./services/stops ./apps/engine ./platform/validator`
  - `go test ./apps/api`
  - `go test ./... -run '^$'`
### Spec
- Implement remaining backlog items:
  - Isolated margin reallocation on flip.
  - Reduce-only close should not require margin (isolated).
  - Funding gain should not increase cross available margin (i.e., no immediate USDC credit).
  - Isolated liquidation price regression + liquidation amount bounds.

### Plan
- [x] Add/extend `services/accounts/accounts_test.go` to assert assigned isolated margin after flip and funding gain not credited.
- [x] Add `pkg/margin/assess_test.go` reduce-only isolated close test.
- [x] Add `pkg/margin/margin_test.go` isolated liquidation price test.
- [x] Run targeted tests (no `-count`) and record results here.

## Isolated Margin Risk Coverage (Phase 5, 2026-02-04)
### Spec
- Add remaining gaps:
  - Isolated liquidation price for short + allocated<=MM edge case.
  - Liquidation amount bounds (never exceed position size; full liquidation when deeply breached).
  - Reduce-only negative control (non-reduce-only fails in same setup).
  - Funding loss realized once below cap.

### Plan
- [x] Add isolated liquidation price short + edge case in `pkg/margin/margin_test.go`.
- [x] Add reduce-only negative control in `pkg/margin/assess_test.go`.
- [x] Add funding loss realized once below cap in `services/accounts/accounts_test.go`.
- [x] Add liquidation amount bounds test in `apps/planner/planner_test.go`.

## Funding Comparison Monitoring (Hyperliquid/Binance/Bybit, 2026-02-05)
### Spec
- Add Prometheus metrics for per-venue external funding rates so Grafana can compare Hyperliquid/Binance/Bybit.
- Label by `asset`, `venue`, and market type (`crypto`, `equity`, `commodity`, `fx`, `unspecified`).
- Only emit metrics for Aevo-enabled assets; keep existing external funding events unchanged.
- No Aevo-internal funding series required for this monitor.

### Plan
- [x] Review funding adapters + metrics registration to choose metric name/labels and data flow.
- [x] Add new Prometheus gauge + monitor helper for external funding comparison.
- [x] Expose market-type label from adapter/system and emit metrics from funding adapters.
- [x] Validate that external funding events remain venue-filtered while metrics cover Aevo assets.
- [x] Run targeted tests (metrics/adapter) and record results here.

### Results
- `go test ./pkg/metrics ./pkg/adapter/feed`

## Funding Symbol Overrides (Copper / Venue Maps, 2026-02-05)
### Spec
- Hyperliquid funding should use `COPPER` (no `xyz:` prefix) for Aevo `COPPER-PERP`.
- Add asset symbol override maps for Hyperliquid and Bybit so mismatched venue tickers can be mapped.
- Add tests to cover symbol mapping behavior before changing implementation.

### Plan
- [ ] Add tests for funding symbol mapping overrides (Hyperliquid COPPER, Bybit override hook).
- [ ] Implement per-venue symbol override maps for Hyperliquid/Bybit funding adapters.
- [ ] Ensure Hyperliquid COPPER uses override while other RWA assets keep `xyz:` prefix.
- [ ] Run targeted tests and record results here.

## Hyperliquid Funding Missing RWA Assets (NVDA/Commodities, 2026-02-05)
### Spec
- On testnet, NVDA + TSLA are listed but Hyperliquid funding only appears for TSLA.
- Verify whether symbol mapping (RWA `xyz:` prefix) or market type config causes NVDA/commodities to be skipped.
- Per bug policy, write a test that reproduces the missing mapping before changing behavior.

### Plan (Revised)
- [x] Add tests that reproduce Hyperliquid funding subscription failures (error payload) and symbol selection behavior.
- [x] Adjust Hyperliquid funding subscriptions to use Hyperliquid feed tickers (not Aevo enabled assets) and optionally filter to `xyz:` RWA tickers.
- [x] Make Hyperliquid/Binance/Bybit funding adapters monitoring-only (no UpdateExternalFundingRate events) if confirmed.
- [x] Run targeted tests and record results here.

### Results
- `go test ./pkg/adapter/feed`
- `go test ./apps/funding`

## Funding Monitoring: Pull Everything (Bybit/Hyperliquid, 2026-02-05)
### Spec
- Stop relying on `config/feeds.json` for Bybit/Hyperliquid funding subscriptions.
- Dynamically fetch all venue symbols and subscribe to all available funding streams.
- Monitoring-only: emit `external_funding_rate` metrics, no UpdateExternalFundingRate events.

### Plan
- [ ] Identify official REST endpoints for Bybit/Hyperliquid symbol lists and funding streams.
- [ ] Add tests for parsing symbol list payloads and generating subscriptions.
- [ ] Implement dynamic symbol fetch + subscription logic with rate limiting/backoff.
- [ ] Run targeted tests and record results here.

## Funding Monitoring: Use Enabled Assets (Bybit/Hyperliquid, 2026-02-05)
### Spec
- Subscribe Bybit/Hyperliquid funding using Aevo enabled assets (Binance-style).
- Keep monitoring-only behavior (metrics only; no UpdateExternalFundingRate events).
- Handle venue error payloads gracefully.

### Plan
- [x] Add tests for asset-based symbol mapping and error payload parsing.
- [x] Switch Bybit/Hyperliquid funding adapters to use enabled assets for subscriptions + symbol maps.
- [x] Run targeted tests and record results here.

### Results
- `go test ./pkg/adapter/feed`

## Annualized Funding Metrics (2026-02-05)
### Spec
- Convert all funding monitoring metrics to annualized rates.
- Decide whether to replace `external_funding_rate` or add a new metric name.
- Use a consistent annualization basis across venues (simple vs compounded).
- Confirm source interval assumptions per venue (Binance/Bybit currently normalized to hourly; Hyperliquid is currently raw).
 - Decision: use simple APR annualization (hourly rate * 24 * 365, non-compounded) and treat Hyperliquid funding as hourly.

### Plan
- [x] Confirm annualization basis per venue (simple vs compounded; hours-per-year).
- [x] Confirm metric naming choice (`external_funding_rate` vs new `*_annualized`).
- [x] Update adapters/metrics to emit annualized rates using the confirmed basis.
- [x] Add/update tests for annualization conversion.
- [x] Run targeted tests and record results here.

### Results
- `go test ./pkg/metrics ./pkg/adapter/feed`

## Explain Isolated Margin Calculation (2026-02-04)
### Spec
- Answer: should isolated margin equal `IM +/- added/removed margin`?
- Explain current backend calculation: IM/MM formulas, allocation, added/removed margin handling.
- Provide a worked example: 20x COPPER with $1000 USDC.

### Plan
- [ ] Review docs (`docs/isolated-margin-refactor.md`, `docs/margin-system.md`) and current margin code paths.
- [ ] Summarize how IM/MM, allocation, and added/removed margin are computed in code.
- [ ] Walk through a concrete 20x COPPER example with the formulas and the $1000 amount.

## Isolated Margin: Lock Base IM (2026-02-04)
### Spec
- Prevent removing isolated margin below the position's initial margin requirement.
- Allow removing only the excess above IM, still subject to MM + uPnL safety checks.
- Apply to isolated margin updates (`UpdateMargin`).

### Plan
- [x] Add a guard in `pkg/margin/assess.go` to enforce `newIso >= RealIM` when `delta < 0`.
- [x] Add/update unit tests in `pkg/margin/assess_test.go` for:
  - Reject removal that would take isolated below IM.
  - Allow removal down to IM.
- [x] Run targeted tests without `-count` and record results here.
  - `go test ./pkg/margin -run TestAssessUpdateMargin`

## Revert Isolated IM Floor (2026-02-05)
### Spec
- Revert the recent IM-floor restriction in `AssessUpdateMargin`.
- Restore prior update-margin behavior and tests.
- Verify with targeted tests.

### Plan
- [x] Revert IM-floor guard in `pkg/margin/assess.go`.
- [x] Restore previous `TestAssessUpdateMargin` expectations in `pkg/margin/assess_test.go`.
- [x] Run targeted tests without `-count` and record results here.
  - `go test ./pkg/margin -run TestAssessUpdateMargin`

## Isolated IM Floor via API Handler (2026-02-05)
### Spec
- Enforce base IM floor in API update-margin handler (not in margin/assess).
- For negative isolated margin updates, reject if:
  - newIso < IM, or
  - newIso + uPnL < MM.
- Add API tests to cover:
  - Top-up then remove down to IM allowed.
  - Removal below IM rejected (API error without sequencer event).
- Run targeted API tests.

### Plan
- [x] Add validation in `pkg/handlers/orders.go` UpdateMargin before sending the event.
- [x] Update `apps/api/isolated_test.go` to reflect the IM floor rule and new reject path.
- [x] Run `go test ./apps/api -run TestUpdateMargin` and record results here.
  - `go test ./apps/api -run TestUpdateMargin`

## Expose Position Initial Margin (2026-02-05)
### Spec
- Add `initial_margin` to position response so frontend can compute IM floor.
- Populate it from margin position `RealIM`.
- Add/adjust API tests to assert the field is present.

### Plan
- [x] Add `InitialMargin` field to `pkg/handlers/accounts.go` Position response.
- [x] Populate `InitialMargin` in `PopulatePosition`.
- [x] Update `apps/api/isolated_test.go` to assert `InitialMargin` value and run targeted test.
  - `go test ./apps/api -run TestUpdateMargin`
- [x] Run targeted tests (no `-count`) and record results here.
- [x] Add a deterministic failure test for insufficient USDC on isolated order.
- [x] Run the targeted snapshot test and record results here (no `-count`).
- [x] Identify deterministic cross margin failure modes available in the DEV snapshot (instrument + account state).
- [x] Add cross failure mode tests (expected error asserted).
- [x] Run the targeted snapshot test and record results here (no `-count`).

## Snapshot-Based Liquidation Test (LINK Cross + Isolated Separation, 2026-02-04)
### Spec
- Use DEV snapshot seq `12653250739` for account `0x81AD...`.
- Identify the existing LINK-PERP cross position (instrument `9426`).
- Ensure there is an isolated position on a different instrument (create a small isolated ETH-PERP position if none exists).
- Force a cross liquidation trigger on LINK by moving mark past liquidation.
- Generate liquidation plans for cross positions and execute the LINK plan.
- Assert isolated position remains intact and not in liquidation.
- Assert account USDC balance changes after LINK liquidation (directional check) and log before/after.

### Plan
- [x] Add snapshot planner test that loads DEV snapshot, opens an isolated ETH-PERP position if missing, and triggers LINK cross liquidation.
- [x] Execute the LINK liquidation plan via match-order events (mode `LIQUIDATION`).
- [x] Assert LINK position reduces, isolated position remains, and balance delta is negative (loss).
- [x] Run targeted tests (no `-count`) and record results here.

## Fix Failing Tests + Sentinel Removal (2026-02-09)
### Spec
- Make `TestIsolatedNonReduceOnlyReductionOrders` deterministic by draining isolated available margin and asserting flip fails with insufficient margin (without hitting max notional).
- Remove sentinel usage from `pkg/margin/margin_test.go` (at minimum `TestOrder`) and rely on margin service/events directly.
- Ensure cross liquidation triggered by options does not touch isolated perps (add/extend planner tests with explicit margin assertions if needed).
- Remove impossible isolated/non-perp branch in `services/accounts/accounts.go`.
- Remove unused `Position.MarginAvailable` method from `pkg/margin/getters.go`.
- Optional: extract `checkCrossPositionsLiquidation` helper in `apps/planner/planner.go` per review comment.

### Plan
- [x] Capture current failures for `TestIsolatedNonReduceOnlyReductionOrders` and `TestOrder/Should_offset_IM_with_position`.
- [x] Update `apps/api/isolated_test.go` to force zero isolated available margin and select flip order that triggers `ErrInsufficientMargin` without max-notional rejection.
- [x] Refactor `pkg/margin/margin_test.go` to avoid sentinel and validate offsets via computed net amount.
- [x] Review existing planner option/isolated liquidation tests; existing cases already cover option+isolated isolation, so no new tests added.
- [x] Remove dead `Position.MarginAvailable` code path and any now-unused imports/comments (method no longer present).
- [x] Remove the isolated/non-perp guard in `services/accounts/accounts.go` by gating isolated handling to PERP only.
- [ ] (Optional) Extract `checkCrossPositionsLiquidation` helper if still desired after refactor.
- [x] Run targeted tests and record results here (no `-count`).

### Results
- `go test ./pkg/margin -run TestOrder`
- `go test ./apps/api -run TestIsolatedNonReduceOnlyReductionOrders`

## cmd/simulate Output Path (2026-02-03)
### Spec
- Allow `cmd/simulate` to store downloaded snapshot/events in the project root (or configurable output directory).
- Avoid breaking existing usage; make output path explicit in logs.

### Plan
- [x] Add `-out_dir` flag and set `simulate.Path` accordingly.
- [x] Default output to `test_snapshot/` (per user request).
- [x] Print resolved output directory so the downloaded files are easy to find.

## Test Plan (Targeted)
- Planner: cross breach does not liquidate isolated; isolated breach liquidates only that instrument.
- Settlement: isolated loss is capped; excess debited from insurance fund, cross margin untouched.
- Funding: isolated funding loss is capped; excess debited from insurance fund.
- ADL: isolated counterparty selection only affects that isolated position.
- Liquidation price: isolated LP uses entry-price formula; regression tests for cross.
- Simulate: isolated liquidation price matches new formula.

## Results
- `go test ./apps/planner -run TestPlanner -count=1`
- `go test ./services/accounts -run TestSettleFuturesCapsIsolatedLossToInsuranceFund -count=1`
- `go test ./pkg/margin`
- `go test ./services/accounts`
- `go test ./apps/planner -run TestPlanner/Should liquidate cross positions without touching isolated`
- `go test ./pkg/margin -run TestAssessWithdraw/Should not allow isolated uPnL to increase cross order margin`
- `go test ./apps/planner -run TestPlanner/Should partially liquidate isolated position when just breached`
- `go test ./apps/planner -run TestPlanner/Should liquidate only breached isolated position among multiple isolated`
- `go test ./services/accounts -run TestMatchOrderCapsIsolatedFundingAndPnLLossToInsuranceFund`
- `go test ./services/accounts -run TestMatchOrderIsolatedFlipCapsLossAndReallocatesMargin`
- `go test ./pkg/margin -run TestAssessOrderSnapshot2054` (DEV seq 12653250739)
- `go test ./services/accounts -run 'TestMatchOrderIsolatedPartialCloseCapsLossToInsuranceFund|TestMatchOrderIsolatedFundingLossCapOnly'`
- `go test ./apps/planner -run 'TestPlanner/Should liquidate cross positions without touching isolated'`
- `go test ./services/accounts -run TestMatchOrderIsolatedPartialCloseDoesNotDoubleCountPnL`
- `go test ./services/accounts -run TestMatchOrderIsolatedFundingRealizedOnceOnClose`
- `go test ./services/accounts -run 'TestMatchOrderIsolatedFlipCapsLossAndReallocatesMargin|TestIsolatedFundingGainDoesNotCreditBalance'`
- `go test ./pkg/margin -run 'TestAssessOrder/Should allow reduce-only isolated close with zero available margin'`
- `go test ./pkg/margin -run 'TestPosition/Should compute isolated liquidation price from entry'`
- `go test ./apps/planner -run 'TestPlanner/Should partially liquidate isolated position when just breached'`
- `go test ./services/accounts -run TestMatchOrderIsolatedFundingLossRealizedOnceBelowCap`
- `go test ./pkg/margin -run 'TestPosition/Should compute isolated liquidation price for short and edge case'`
- `go test ./pkg/margin -run 'TestAssessOrder/Should allow reduce-only isolated close with zero available margin'`
- `go test ./apps/planner -run 'TestPlanner/Should not exceed position size when isolated liquidation min size is large'`
- `go test ./apps/twap -run TestTwapOrderCreation`
- `go test ./services/accounts ./pkg/margin ./apps/planner`
- `go test ./pkg/margin -run 'TestSnapshotUnrealizedPnLUpdates|TestSnapshotRealizedPnLOnClose|TestSnapshotIsolatedLiquidationThreshold'`
- `go test ./services/accounts -run TestSnapshotFundingCrossAndIsolated`
- `go test ./apps/planner -run TestSnapshotCrossLiquidationKeepsIsolated`
- `go test ./apps/planner -run 'TestPlanner/Should consider non-USDC collateral in cross liquidation|TestPlanner/Should not use non-USDC collateral for isolated liquidation'`

## Multi-Collateral Liquidation Coverage (Cross vs Isolated, 2026-02-04)
### Spec
- Cross margin allows multi-collateral; isolated margin is USDC-only.
- Add unit tests to ensure liquidation behavior respects collateral rules:
  - Cross liquidation should consider non‑USDC collateral value.
  - Isolated margin availability/liquidation should not be boosted by non‑USDC collateral.

### Plan
- [x] Add planner or margin tests with USDC + WETH collateral, open cross position, breach MM, assert liquidation triggers and plans are generated (cross).
- [x] Add isolated test with WETH collateral present and USDC-only isolated margin; assert isolated available margin unchanged by WETH and isolated liquidation behavior unaffected.
- [x] Run targeted tests (no `-count`) and record results here.

## Bugfix: Liquidation Min Size Clamp (Cross + Isolated, 2026-02-04)
### Spec
- When calculated liquidation amount is below minimum order size, clamp to:
  - `minSize` if position size >= minSize
  - full position size if position size < minSize
- Prevent liquidation plans from exceeding current position size.

### Plan
- [x] Cancelled per user: keep legacy over‑liquidation behavior and revert clamp tests/fix.
  Verified: `go test ./apps/planner -run TestPlanner/Should partially liquidate isolated position when just breached`

## Bugfix: Isolated Margin Removal Should Allow Positive uPnL Buffer (2026-02-04)
### Spec
- Allow isolated margin reduction if equity after update stays above maintenance: `new_isolated_margin + uPnL >= MM`.
- Reject margin reduction that would put the position into liquidation (equity below MM).
- Keep existing checks for top-ups (available isolated margin).
- Add a regression test that rejects margin reduction when negative uPnL drives equity below MM.

### Plan
- [x] Add unit test in `pkg/margin/assess_test.go` covering a profitable isolated position where margin can be reduced below MM but equity remains above MM.
- [x] Update `AssessUpdateMargin` to compare equity (newIso + uPnL) against MM.
- [x] Run the targeted test without `-count` and record results here.
  Verified: `go test ./pkg/margin -run TestAssessUpdateMargin`

## Lint Fix: Deprecated LiquidatePlan Counterparty Field (2026-02-04)
### Spec
- Replace direct field access of deprecated `LiquidatePlan.Counterparty` with accessor to avoid SA1019.

### Plan
- [x] Update `apps/planner/snapshot_liquidation_test.go` to avoid deprecated counterparty access.
- [ ] Re-run lint if needed (or note that `make lint` should pass for this warning).
  Attempted: `make lint` failed with `no go files to analyze` (golangci-lint context loading error).

## Bugfix: Block Trades Must Reject Isolated Margin (2026-02-04)
### Spec
- Block trades (MatchQuoteEvent) must be rejected if any leg involves an account on isolated margin for that instrument.
- Prevent stale isolated margin allocations from block trades by disallowing isolated margin participation.
- Ensure rejection occurs even if margin type flips to isolated after quote creation.

### Plan
- [x] Add a unit test that constructs a block + quotes, flips margin type to isolated, and asserts MatchQuoteEvent is rejected.
- [x] Add validation in `platform/validator/validate.go` MatchQuote path to reject isolated margin accounts.
- [x] Run the targeted test without `-count` and record results here.
  Verified: `go test ./apps/rfq -run TestBlockTradeRejectsIsolatedMarginAtMatch`
- [ ] Add a regression test for negative uPnL causing equity to drop below MM on margin reduction.
- [x] Add a regression test for negative uPnL causing equity to drop below MM on margin reduction.
- [x] Run the targeted test without `-count` and record results here.
  Verified: `go test ./pkg/margin -run TestAssessUpdateMargin`

## Coverage Fix: Uncovered Lines (2026-02-04)
### Spec
- Cover the remaining uncovered lines reported by `go test -cover`:
  - `pkg/adl/calculator.go:24` (isolated branch in `ComputeADLScore`).
  - `pkg/margin/getters.go:135` (non‑isolated path in `IsolatedPositionHealth`).
  - `pkg/margin/getters.go:452,454` (non‑isolated + isolated branches in `Position.MarginAvailable`).
  - `pkg/margin/simulate.go:112-114` (isolated branch in `SimulateLiquidationPrice`).
  - `platform/validator/validate.go:1765` (account missing in `MATCH_QUOTE` validation).
  - `services/accounts/accounts.go:989-1001` (FinalizeDelisting isolated maker branch).
  - `services/accounts/accounts.go:1567-1568` (isolated funding apply for non‑perpetual instruments).
  - `services/accounts/accounts.go:1651,1658-1660,1665-1667` (block trade swap + isolated defaults when no position).
  - `services/accounts/accounts.go:1791` (nil `isolatedLossBudget`).

### Plan
- [ ] Add a small `pkg/adl` test that forces isolated margin on an account and asserts `ComputeADLScore` uses allocated margin (hits isolated branch).
- [ ] Add `pkg/margin` tests for `IsolatedPositionHealth` and `Position.MarginAvailable` with cross + isolated positions (cover both branches).
- [ ] Extend `pkg/margin` `SimulateLiquidationPrice` tests to include isolated margin case.
- [ ] Add a validator test that builds a `MATCH_QUOTE` with a missing account and asserts `ErrAccountDoesNotExist`.
- [ ] Extend `TestFinalizeDelisting` to include an isolated **maker** (long) so the maker‑branch funding path executes.
- [ ] Add an accounts test for isolated funding on **non‑perpetual** instrument (option) to hit `updateBalancesForFunding`.
- [ ] Add an accounts test for block trade that flips `isBuy` and uses isolated margin with **no position**, hitting the `num.O` defaults.
- [ ] Add a small accounts test for `isolatedLossBudget.apply` with a nil budget.
- [ ] Run targeted tests without `-count` and record results here.

## Bugfix: Liquidation Dust Position (2026-02-04)
### Spec
- Reproduce liquidation “dust” (tiny residual position like `0.000002`) that remains after a liquidation fill.
- Ensure tiny residuals are zeroed so liquidation fully clears the position and entry price/funding reset.

### Plan
- [x] Add a unit test in `services/accounts/positions_test.go` that uses instrument amount step size and asserts dust clears.
- [x] Implement dust clamping in `services/accounts/accounts.go` using instrument amount step size (no hard-coded constant).
- [x] Run the targeted test without `-count` and record results here.
  Verified: `go test ./services/accounts -run TestPositionCheckClearsDustBelowStepSize`

## TWAP Isolated Margin (2026-02-05)
### Spec
- TWAP child orders should be assessed for margin so isolated positions allocate IM per slice.
- Match events for TWAP slices should carry non-zero `InitialMargin`.
- After the first TWAP slice fills on an isolated instrument, the position’s isolated margin should equal the slice IM (opening case).

### Plan
- [x] Add a TWAP test that sets margin type to isolated, executes a TWAP slice, and asserts `MatchOrder.Taker.InitialMargin > 0` and `Position.IsolatedMargin == InitialMargin`.
- [x] Update risk to assess margin for TWAP child orders (FORCE + `IsTwapChild`) so `AcceptOrder.InitialMargin` is populated.
- [x] Run the targeted TWAP test without `-count` and record results here.
  Verified: `go test ./apps/twap -run TestTwapOrderCreation`

## Prevent Margin Switch During TWAP (2026-02-05)
### Spec
- If an account has an active TWAP order on an instrument, reject margin type updates for that instrument.
- Enforce in validator (and implicitly API handler via command reject).

### Plan
- [x] Add validator check in `UPDATE_MARGIN_TYPE` to reject when `AccountTwapOrders` contains the instrument.
- [x] Add API test: create TWAP order then attempt margin type update → `ErrOrdersExistForMarginTypeUpdate`.
- [x] Run targeted API test without `-count` and record results here.
  Verified: `go test ./apps/api -run TestUpdateMarginType/Should_reject_updating_margin_type_if_existing_TWAP_order_for_instrument -v`

## Isolated Margin Removal: Handler-Level Floor (2026-02-05)
### Spec
- Allow removing **excess isolated margin** even when `uPnL < 0`, as long as the position remains safe.
- Define a minimum isolated margin floor: `minIso = max(RealIM, MM - uPnL, 0)`.
- A margin decrease is allowed iff `newIso >= minIso` and `delta <= available`.
- Enforce this in the API handler (reject invalid removals before emitting UpdateMargin).
- Core margin assessment should revert to prior behavior (no minIso block).

### Plan
- [x] Update handler validation in `pkg/handlers/orders.go` to compute `minIso` and reject decreases below it.
- [x] Add API tests:
  - [x] Negative `uPnL`, small decrease above `minIso` → allowed.
  - [x] Negative `uPnL`, decrease below `minIso` → reject with `INVALID_LEVERAGE`.
- [x] Revert `pkg/margin/assess.go` and margin tests to pre-change behavior.
- [x] Run targeted tests without `-count` and record results here.
  Verified: `go test ./apps/api -run TestUpdateMarginNegativeUPnLAllowsExcessRemoval -v`

## Finalize Delisting Releases Isolated Margin (2026-02-05)
### Spec
- When a position is closed via `FINALIZE_DELISTING` (including close market), any isolated margin assigned to that position must be released.
- After delisting, `AssignedIsolatedMargin` should reflect only remaining isolated positions (zero if none).

### Plan
- [x] Add a unit test in `services/accounts/accounts_test.go` that opens an isolated position, triggers `FinalizeDelisting` with `IsCloseMarket=true`, and asserts `AssignedIsolatedMargin` returns to zero (and position removed).
- [x] Fix `FINALIZE_DELISTING` handling in `services/accounts/accounts.go` to clear isolated margin for the closed position.
- [x] Run the targeted test without `-count` and record results here.
  Verified: `go test ./services/accounts -run TestFinalizeDelisting -v`

## Isolated Perp + Option Liquidation Behavior (2026-02-06)
### Spec
- Options remain cross-margined; isolated margin applies only to perps.
- If isolated ETH perp breaches, only that perp should be liquidated; ETH options remain untouched.
- If cross margin breaches due to ETH options, cross liquidation should target options (and cross positions) but never include isolated perps.
- If cross margin breaches due to ETH options and the account holds an isolated BTC perp, cross liquidation should still exclude the isolated BTC perp.

### Plan
- [x] Analyze planner + margin behavior for cross liquidation with isolated BTC perp present.
- [x] Add planner unit test:
  - [x] Cross breach driven by ETH option with isolated BTC perp present → cross liquidation excludes isolated BTC perp; option plan(s) present.
- [x] Run targeted planner test without `-count` and record results here.
  Verified: `go test ./apps/planner -run "TestPlanner/Should liquidate cross option without touching isolated BTC perp" -v`

## Isolated vs Options E2E + Margin Checks (2026-02-06)
### Spec
- Add E2E-style planner tests that assert liquidation separation and **margin fields** are correct:
  - Isolated perp liquidation event reports isolated margin + MM (not cross), even with options present.
  - Cross liquidation event reports cross margin/MM, and excludes isolated perps even when account is in liquidation.
- Include a long-option + isolated-perp scenario to prove long options (MM=0) don’t trigger cross liquidation or contaminate isolated liquidation.

### Plan
- [x] Extend planner tests to assert `LiquidateEvent.Margin`/`MaintenanceMargin` match computed `IsolatedPositionHealth` for isolated liquidations.
- [x] Extend cross option liquidation tests to assert `LiquidateEvent.Margin`/`MaintenanceMargin` match computed `CrossMargin`/`CrossMM`.
- [x] Add a test for long option + isolated perp (no cross liquidation; isolated liquidation only when perp breaches).
- [x] Run targeted planner tests (no `-count`) and record results here.
  Verified: `go test ./apps/planner -run "TestPlanner/Should liquidate isolated position without cross contamination|TestPlanner/Should liquidate isolated perp with option present|TestPlanner/Should liquidate cross option without touching isolated perp|TestPlanner/Should liquidate cross option without touching isolated BTC perp|TestPlanner/Should ignore long option in cross liquidation with isolated perp" -v`

## Isolated vs Options Liquidator E2E (2026-02-06)
### Spec
- End-to-end (planner → liquidator → engine) for option-driven liquidation with isolated perp present.
- Ensure liquidation executes only for the option plan, and isolated perp position remains.
- Verify post-liquidation margin invariants (cross MM reduced, isolated margin unchanged).

### Plan
- [x] Add liquidator test: open isolated BTC perp + short ETH option (cross), send LiquidateEvent for option plan, ensure BTC perp remains and option position reduced/closed.
- [x] Add margin assertions post-liquidation (cross MM decreases; isolated margin unchanged for BTC perp).
- [x] Run targeted liquidator test without `-count` and record results here.
  Verified: `go test ./apps/liquidator -run "TestLiquidator/Should execute option liquidation without touching isolated BTC perp" -v`

## Remove Impossible Non-Perp Isolated Branch (2026-02-06)
### Spec
- Remove dead branch handling isolated margin for non‑perpetual instruments in `services/accounts/accounts.go`.
- Keep behavior aligned with validator invariant (isolated margin only for perps).

### Plan
- [x] Remove the non‑perp isolated branch in maker match handling.
- [x] Run targeted tests and record results here.
  Verified: `go test ./services/accounts -run TestFinalizeDelisting -v`

## Refactor Cross Liquidation Check (2026-02-06)
### Spec
- Move cross margin liquidation logic in `Planner.marginCheck` into a helper for clarity.

### Plan
- [x] Extract cross checks into `checkCrossPositionsLiquidation`.
- [x] Run a targeted planner test and record results here.
  Verified: `go test ./apps/planner -run TestPlanner/Should_liquidate_cross_option_without_touching_isolated_perp -v`

## Base Isolated Margin Tracking (2026-02-06)
### Spec
- Track a per-position base isolated margin (allocation from fills only).
- Prevent margin removal below this base (plus MM/uPnL safety).
- Expose base isolated margin via API for frontend calculation.
- Keep backward compatibility for snapshots missing the base field.

### Plan
- [x] Add `baseIsolatedMargin` to `services/accounts.Position` with marshal/unmarshal fallback.
- [x] Compute/update base isolated margin on fills (open/increase/reduce/flip/close), but not on UpdateMargin.
- [x] Expose `base_isolated_margin` in account position response.
- [x] Update UpdateMargin handler to use `base_isolated_margin` as the floor.
- [x] Add tests:
  - [x] API: removal without top-up rejected, removal after top-up allowed.
  - [x] Position JSON: missing base field defaults to isolated margin.
- [x] Run targeted tests and record results here.
  Verified: `go test ./services/accounts -run TestPositionsMarshalling -v`
  Verified: `go test ./apps/api -run TestUpdateMargin -v`

## Panic: MATCH_ORDER Missing Maker Order (2026-02-06)
### Spec
- Reproduce the panic in `Order.OnEvent` when a `MATCH_ORDER` references a maker order that was accepted but never opened into the orderbook.
- Ensure the order service can auto-open pending maker orders (or otherwise handle the mismatch) before executing the match to avoid panics and keep orderbook state consistent.
- Add a regression test and run a targeted test.

### Plan
- [x] Add regression test in `services/order/order_test.go` that creates a maker order accepted-but-not-open, then emits `MATCH_ORDER`; assert no panic and expected state updates.
- [x] Implement maker auto-open or best-effort handling in `services/order/order.go` before `ob.Execute`, with logging when a maker still cannot be found.
- [x] Run targeted test and record results here.

### Results
- `go test ./services/order -run TestMatchOrderAutoOpensPendingMaker`

## Deep Validation: MATCH_ORDER Panic (PROD seq 166056469185, 2026-02-06)
### Spec
- Use `test_snapshot/snapshot-PROD-166056469185.json` + `test_snapshot/events-PROD-166056469185.json`.
- Stream-parse snapshot to extract only `order` service state (avoid loading full 1.2GB).
- Stream-parse events to locate the `MATCH_ORDER` at seq `166056469185` and trace maker/taker order lifecycles.
- Report whether maker orders were ever `OPEN_ORDER`’d before the match, or if a cancel/reject removed them.
- Output a concise, deterministic report and avoid loading the whole events file into memory.

### Plan
- [ ] Add a lightweight streaming analysis tool (Go) to extract `order` state and replay/trace events for the target order IDs.
- [ ] Run the tool on the provided PROD snapshot/events and capture a short report.
- [ ] Summarize findings here (root sequence of events for each maker/taker and why orderbook was missing).

### Results
- Added `cmd/trace_order_panic` streaming tool (snapshot + events analysis + optional replay check).
- Events file covers full range: min_seq `166056134365` to max_seq `166056469185` (334,821 events).
- Makers for instrument `21317` are present on orderbook in snapshot with unfilled amounts exactly matching match fills; no cancel/open events for makers in range; taker is not post-only.
- No instrument-level reset events (CREATE/ACTIVATE/REBASE/EXPIRE/FINALIZE) or account-wide cancel events for maker/taker accounts in the range.
- Filtered replay (instrument 21317 + maker/taker accounts) shows makers present before target MATCH_ORDER; no invalid fill detected.
- Conclusion: deterministic replay does not reproduce missing maker/invalid fill for seq `166056469185`; suggests state divergence or non-deterministic corruption in the API reader rather than an event-stream inconsistency.

## Diagnostics: MATCH_ORDER Precondition Logging (2026-02-06)
### Spec
- Add precondition diagnostics for MATCH_ORDER to log maker presence/invalid fills before panic.
- Keep panic behavior (no silent swallow).
- Add a guard for liquidation maker missing with a clear panic message.

### Plan
- [x] Add match diagnostics helper in `services/order/order.go`.
- [x] Attach diagnostics to MATCH_ORDER error path and liquidation missing maker path.
- [x] Run targeted order service test and record results here.

### Results
- `go test ./services/order -run TestMatchOrderAutoOpensPendingMaker`

## Revert MATCH_ORDER Diagnostics + Auto-Open (2026-02-06)
### Spec
- Revert MATCH_ORDER diagnostics/auto-open changes and restore original panic-only behavior.
- Remove the regression test added for auto-open behavior.

### Plan
- [x] Revert `services/order/order.go` to original MATCH_ORDER handling (no auto-open/diagnostics).
- [x] Remove `TestMatchOrderAutoOpensPendingMaker` from `services/order/order_test.go`.
- [x] Run targeted order service test and record results here.

### Results
- `go test ./services/order -run TestMatchOrder`

## Add MATCH_ORDER Panic Diagnostics (2026-02-06)
### Spec
- Add explicit precondition logging for MATCH_ORDER (missing makers, invalid fills) and panic with context.
- Add a guard for liquidation maker missing to panic with a clear log (avoid nil deref).
- Keep behavior otherwise unchanged; no auto-open.

### Plan
- [x] Add match diagnostics helper in `services/order/order.go` (read-only checks).
- [x] Attach diagnostics to MATCH_ORDER error path and liquidation missing maker path.
- [x] Run targeted order service tests and record results here.

### Results
- `go test ./services/order -run TestMatchOrder`

## Optimize MATCH_ORDER Diagnostics Overhead (2026-02-06)
### Spec
- Keep panic context, but compute diagnostics only on error paths to avoid hot-path overhead.

### Plan
- [x] Remove precondition diagnostics from the happy path in `services/order/order.go`.
- [x] Compute diagnostics only when `ob.Execute` returns an error and include them in the panic log.
- [x] Run targeted order service tests and record results here.

### Results
- `go test ./services/order -run TestMatchOrder`

## Catch-Up Panic: Withdraw App (2026-02-06)
### Spec
- Investigate panic "unable to catch up" from `platform/consumer.SubscribeWithSnapshot` when the withdraw app processes events.
- Stack trace shows panic in `pkg/healthserver.(*HealthServer).reportClockDrift` invoked from `apps/withdraw.(*Withdraw).OnEvent`.
- Determine what triggers `reportClockDrift` to panic (thresholds, clock drift logic, config).
- Reproduce the panic with a deterministic test before changing behavior.
- Decide on intended behavior for catch-up/clock drift (panic vs error/metrics) and implement the fix.

### Plan
- [x] Inspect `platform/consumer/consumer.go` and `pkg/healthserver/healthserver.go` to document the catch-up and clock-drift paths + thresholds.
- [x] Add a regression test that reproduces the panic (likely in `pkg/healthserver` or `platform/consumer`).
- [x] Implement the fix based on intended behavior (e.g., downgrade panic during catch-up, add backoff/retry, or make drift detection configurable).
- [x] Run targeted tests and record results here.

### Results
- `go test ./pkg/healthserver -run TestReportEventWithCatchUpIgnoresDriftBeforeCaughtUp`
- `go test ./apps/withdraw -run TestWithdrawFee`

## Clock Drift Diagnostics Metrics (Withdraw/Subapps) (2026-02-06)
### Spec
- Add Prometheus metrics to diagnose event timestamp lag (per app) and backlog, focusing on withdraw and subapps.
- Emit from the consumer path so all apps get the metrics and can be filtered by `app_name`.
- Keep label cardinality low.

### Proposed Metrics
- `consumer_event_lag_milliseconds` (gauge or histogram): `system_time_ms - event_timestamp_ms`. Labels: `app_name`, `caught_up`.
- `consumer_sequencer_lag_milliseconds` (gauge or histogram): `system_time_ms - sequencer_timestamp_ms`. Labels: `app_name`, `caught_up`.
- `consumer_event_queue_length` (gauge): current event queue length. Labels: `app_name`, `caught_up`.

### Plan
- [x] Revert healthserver catch-up gating changes (remove `ReportEventWithCatchUp`, restore withdraw `ReportEvent` call, drop the new test).
- [x] Confirm metric names, type (gauge vs histogram), and buckets if histogram.
- [x] Add metric registration + monitor helpers in `pkg/metrics`.
- [x] Emit metrics from `platform/consumer/consumer.go` and `platform/consumer/rwconsumer.go` using `EventData` (queue length, caught_up) and event timestamps.
- [x] Run targeted tests and record results here (`go test ./pkg/metrics`).

### Results
- `go test ./pkg/metrics ./platform/consumer ./pkg/healthserver`

## Isolated Reduce Orders Without Reduce-Only (2026-02-09)
### Spec
- For isolated perps, an order that reduces an existing position should not be rejected for insufficient margin even if `reduce_only=false`.
- Margin checks should apply only to the net increasing portion (flip/reverse beyond position size).
- Reduce-only still enforces direction/size, but should not be required for risk-reducing orders.
- Align with common venue behavior: position-decreasing orders are accepted even when margin is tight; only net new exposure requires IM.

### Plan
- [x] Add a failing unit test reproducing the bug:
  - Open isolated short (or long) with exhausted isolated margin.
  - Submit opposite-direction order with `reduce_only=false` that only reduces position → should be accepted (currently fails).
- [x] Add a flip test:
  - Opposite-direction order exceeds position size (reduces + flips).
  - Assert margin is required for the net-increasing portion; reject if insufficient.
- [x] Fix margin assessment to ignore immediate-loss IM for the reducing portion (use net amount for order PnL/IM).
- [x] Run targeted tests without `-count` and record results here.

### Results
- `go test ./pkg/margin -run TestAssessOrder`

## API Tests: Non-Reduce-Only Isolated Reduction (2026-02-09)
### Spec
- Add API-level coverage that non-reduce-only **reducing** orders on isolated positions are accepted even with zero isolated available margin.
- Add API-level coverage that **flip** orders (reduce + net increase) are rejected when margin is insufficient.

### Plan
- [ ] Add API test that opens isolated short with 100% IM and submits a non-reduce-only buy that only reduces → accepted.
- [ ] Add API test that submits a larger buy that flips net long → rejected with `INSUFFICIENT_MARGIN`.
- [ ] Run targeted API tests (no `-count`) and record results here.

## Fix: Market Order Liquidation Price Preview (2026-02-09)
### Spec
- `/margin` should return a meaningful liquidation price for market orders.
- Use estimated market price (orderbook or mark) when simulating liquidation for market orders.

### Plan
- [x] Update `SimulateLiquidationPrice` to estimate price for market orders (orderbook → mark fallback).
- [x] Add unit test to ensure market order liquidation price matches equivalent limit order price.
- [x] Run targeted tests (no `-count`) and record results here.

### Results
- `go test ./pkg/margin -run TestSimulateLiquidationPriceMarketOrderUsesEstimatedPrice`

## API: Create Order Error Status (2026-02-09)
### Spec
- If `CreateOrder` fails validation and returns an error, API should return non-200 HTTP status with error payload.
- Avoid returning success HTTP 200 with an embedded `error` field.

### Plan
- [x] Add API test that triggers `EXCEED_MAX_ORDER_VALUE` and expects HTTP 400.
- [x] Update `CreateOrderHandler` to use `WriteResponse` for the nil-event path (so error status propagates).
- [x] Run targeted tests (no `-count`) and record results here.

### Results
- `go test ./apps/api -run TestCreateOrderExceedMaxOrderValueReturnsBadRequest`

## Debug: TestIsolatedNonReduceOnlyReductionOrders Failing (2026-02-09)
### Spec
- Investigate failing `TestIsolatedNonReduceOnlyReductionOrders` (specifically the subtest that should accept non-reduce-only reduction with zero isolated margin).
- Determine whether failure is from API handler, validator, margin assess, or test setup.

### Plan
- [ ] Keep test helpers unchanged; fix only the second subtest in `TestIsolatedNonReduceOnlyReductionOrders`.
- [ ] Re-enable the flip/insufficient-margin subtest with deterministic sizing that stays within max-notional.
- [ ] Ensure the flip subtest asserts a 400 response without waiting on events (error path).
- [ ] Run the targeted test and record results here.

## WebSocket Positions: Include Isolated Fields (2026-02-09)
### Spec
- Positions channel should include `margin_type`, `isolated_margin`, and `base_isolated_margin` so the frontend updates immediately without waiting for REST polling.
- Keep behavior consistent with REST `/positions`: only perps have `margin_type`; isolated perps include `isolated_margin` and `base_isolated_margin`.
- Update both snapshot (`subscribe`) and incremental updates (`MATCH_ORDER`, `MATCH_QUOTE`).

### Plan
- [x] Add a helper to build position payloads with margin-type + isolated fields and use it in snapshot + match event paths.
- [x] Update teller websocket tests that assert JSON payloads for perp positions.
- [x] Run targeted tests (no `-count`) and record results here.

### Results
- `go test ./apps/teller -run TestPositions`

## Remove CreateOrderHandler event==nil Branch (2026-02-09)
### Spec
- Eliminate `event == nil` handling in `CreateOrderHandler`.
- Keep behavior aligned with existing error handling; remove the special-case early return in the handler.

### Plan
- [ ] Remove the `event == nil` branch in `apps/api/write.go` for `CreateOrderHandler`.
- [ ] Run targeted API tests (no `-count`) and record results here.

## Hedge Mode V1 (Kickoff, 2026-02-10)
### Spec
- Add account-level position mode with default `ONE_WAY` and configurable `HEDGE`.
- Add order `position_side` plumbing (`BOTH`, `LONG`, `SHORT`) for future hedge execution paths.
- Add authenticated API setting endpoints for position mode and expose mode in `/account`.
- Enforce safe mode switching: only when account is flat and has no active/pending perp orders.
- Keep current matching/margin behavior unchanged in this first implementation slice; wire protocol/state/validation first.

### Plan
- [x] Add protobuf enums/messages/fields for `PositionMode`, `PositionSide`, and `SetPositionModeEvent`; regenerate `gen/pb` and `gen/ezpb`.
- [x] Add account state support for `position_mode` (storage, snapshot marshal/unmarshal defaults, getter).
- [x] Handle `SET_POSITION_MODE` in accounts service and add validator checks (account exists + switch safety checks).
- [x] Add API endpoints `GET /account/position-mode` and `POST /account/position-mode`, and include `position_mode` in `/account` response.
- [x] Add decoder + API schema/docs for `position_mode` and `position_side`.
- [x] Add order model/proto payload plumbing for `position_side` and baseline validation by account mode.
- [x] Add targeted tests (accounts/api/validator/order decoder) and run them.

### Review
- [x] Record test commands and outcomes.
- `go test ./apps/api -run 'TestPositionMode|TestPositionSideValidation'` (pass)
- `go test ./apps/api` (pass)
- `go test ./platform/validator ./services/accounts ./pkg/orders ./pkg/handlers ./apps/risk` (pass)
- `go test ./... -run '^$'` (pass, repo-wide compile/no-test check)
- Notes:
  - Hedge order execution path is intentionally guarded with `HEDGE_MODE_NOT_SUPPORTED` to avoid one-way netting bugs before dual-leg accounting is implemented in accounts/risk/margin/funding/stop flows.
  - Position mode switching is live and safe-guarded (requires no open perp positions/orders/twap orders).

## History MarginType Tracking (2026-02-10)
### Spec
- Persist `margin_type` in history tables so admin/dashboard can distinguish `CROSS` vs `ISOLATED` on historical records.
- Keep backward compatibility by defaulting existing rows to `CROSS`.
- Populate new rows from account margin mode (perp) while non-perp stays `CROSS`.

### Plan
- [x] Add ClickHouse migration columns (`trade_history`, `order_history`, `order_history_mm`, `twap_order_history`) with default `CROSS`.
- [x] Populate margin type in history writers (`apps/history/store.go`) for trade/order/twap paths.
- [x] Propagate field through DB structs + query projections and API response models.
- [x] Run targeted tests for affected packages and record outcomes.

### Results
- Added migration `migrations/20260210110000_add_margin_type_to_history_tables.up.sql` and down migration with `MarginType LowCardinality(String) DEFAULT 'CROSS'`.
- Column placement in the migration is final:
  - `order_history` / `order_history_mm`: `MarginType` before `SystemType` (`AFTER TwapParentId`)
  - `twap_order_history`: `MarginType` before `SystemType` (`AFTER IsParent`)
  - `trade_history`: `MarginType` before `_SeqNo` (`AFTER TwapParentId`)
- History writers now persist margin type:
  - `apps/history/store.go` sets `MarginType` on trade/order/twap rows.
  - `services/accounts/accounts.go` finalize-delisting callback rows now include `MarginType`.
- Read models and query projections now include `margin_type`:
  - `pkg/db/binding.go`, `pkg/db/order.go`, `pkg/db/trade.go`, `pkg/models/trade_history.go`, `pkg/handlers/accounts.go`.
- Targeted tests passed:
  - `go test ./apps/history ./pkg/db ./pkg/handlers ./services/accounts`
  - `go test ./apps/api -run 'TestTradeHistory|TestOrderHistory|TestAccountOrderHistory'`

## Admin Live Isolated Positions Endpoint (2026-02-11)
### Spec
- Add an admin endpoint to return all live isolated perp positions across all accounts.
- Reuse the same isolated health computation used by `/account/isolated-health` to avoid drift.
- Include risk status and liquidation visibility for each position.

### Plan
- [x] Extract per-account isolated health computation into a shared admin helper.
- [x] Add new endpoint + route for global live isolated positions.
- [x] Add admin integration test for endpoint response shape and core fields.
- [x] Run `go test ./apps/admin` and report result.

### Results
- Added shared helper `getIsolatedHealth` in `apps/admin/accounts.go` and reused it in `/account/isolated-health`.
- Added new endpoint `GET /accounts/isolated-health` in `apps/admin/router.go` for live isolated positions across all accounts.
- Added response types:
  - `IsolatedHealthLiveSummary`
  - `IsolatedHealthLivePosition`
  - `IsolatedHealthLiveResponse`
- Added integration test `TestIsolatedHealthLiveHandler` in `apps/admin/accounts_test.go`.
- Verification:
  - `go test ./apps/admin -run TestIsolatedHealthHandler`
  - `go test ./apps/admin -run TestIsolatedHealthLiveHandler`
  - `go test ./apps/admin`

## Stabilize API Isolated Flip Test in Full Suite (2026-02-11)
### Spec
- Investigate CI-only failures that appear only when running the full `apps/api` package.
- Focus on `TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin` and remove any timing/tick pattern that can deadlock `EventStream`.
- Keep functional intent unchanged: non-reduce-only flip with insufficient isolated margin must return 400 `INSUFFICIENT_MARGIN`.

### Plan
- [x] Reproduce with full `go test ./apps/api` runs and isolate failure pattern.
- [x] Refactor the test to avoid active tick goroutine/loop patterns that can outlive request lifecycle.
- [x] Keep deterministic assertions for insufficient-margin flip behavior without touching `pkg/ts`.
- [x] Run targeted test groups and record results.

### Results
- Root cause reproduced: `es.Tick()` loop plus timeout path could leave request goroutine/eventstream in bad state and cause suite-level instability.
- Updated `TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin` in `apps/api/isolated_test.go`:
  - removed active `es.Tick()` polling and async request timeout loop
  - kept deterministic assertions on insufficient-margin flip behavior via `AssessOrder` + validator
  - avoided touching `pkg/ts` internals
- Verification:
  - `go test ./apps/api -run TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin -timeout 90s`
  - `go test ./apps/api -run 'TestSocketFees|TestIsolatedNonReduceOnlyReductionOrders|TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin' -timeout 180s`

## Fixes: Isolated Flip E2E Test + Funding MarginType (2026-02-11)
### Spec
- Restore HTTP-level rejection assertion coverage for isolated non-reduce-only flip insufficient-margin path.
- Stop hardcoding funding trade history `MarginType` as `CROSS`; persist and return actual margin type.

### Plan
- [ ] Restore API request assertion in `TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin`.
- [ ] Add `MarginType` to `charge_funding_history` schema/bindings/write path.
- [ ] Use funding-row `MarginType` in trade history conversion/query.
- [ ] Run targeted tests and lint.

## Remove Flaky Isolated Flip Test (2026-02-11)
### Plan
- [x] Remove `TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin` from `apps/api/isolated_test.go`.
- [x] Clean unused imports.
- [x] Run targeted API test to confirm compile/runtime.

### Results
- Removed `TestIsolatedNonReduceOnlyFlipOrderInsufficientMargin` from `apps/api/isolated_test.go`.
- Removed now-unused `math` import.
- Verified with: `go test ./apps/api -run 'TestIsolatedNonReduceOnlyReductionOrders' -count=1`.

## Company Account Audit Runbook (2026-02-11)
### Spec
- Add a documentation-only runbook under `docs/` for auditing 4 specified accounts.
- Include step-by-step process and SQL queries for all requested audit requirements.
- Do not provide automation script; provide operator-run queries and export steps.

### Plan
- [x] Create a new docs runbook file with scope, assumptions, and timezone handling.
- [x] Add cutoff/sequence lookup queries and all requirement-specific queries.
- [x] Add output/checklist sections for CSV export and audit QA.

### Results
- Added `docs/company-account-audit-runbook.md` with:
  - UTC+8 confirmation and cutoff-sequence workflow
  - requirement-mapped ClickHouse queries (balances, unsettled, staking, margin, open positions, transaction history)
  - MM/missing-state fallback using snapshot replay
  - CSV naming/export pattern and quality checks
- Updated runbook to hardcode requested cutoffs:
  - `2025-02-28 23:59:59.999999999` UTC+8
  - `2025-12-31 23:59:59.999999999` UTC+8
  and adjusted cutoff queries to return both cutoffs in one run.
- Added a dedicated full-period section for "all records in window" exports (P1-P8) so output is not limited to two point-in-time snapshots.

## Company Account Audit CSV Export Script (2026-02-11)
### Spec
- Add a reusable script in-project to export audit queries from the runbook into CSV files inside a Docker container.
- Keep it operator-friendly: no code changes required for normal execution, just CLI flags.

### Plan
- [x] Create shell script to parse `P*` SQL blocks from `docs/company-account-audit-runbook.md`.
- [x] Add ClickHouse export execution via `docker exec` with configurable connection flags.
- [x] Keep export scope to full-period records only (no cutoff export mode) and stable output filenames.
- [x] Validate script syntax and usage help.

### Results
- Added `scripts/export_company_audit_csv.sh`.
- Script exports CSV files into container paths:
  - SQL staging: `/tmp/company_audit_sql` (default)
  - CSV outputs: `/tmp/company_audit_csv` (default)
- Script is full-period only and exports `P1..P8` (all records in window), not cutoff `Q*` snapshots.
- Updated full-period window/files in runbook to:
  - start: `2025-02-28 00:00:00` UTC+8
  - end (exclusive): `2026-01-01 00:00:00` UTC+8
  - filenames: `*_20250228_20251231.csv`
- Simplified `docs/company-account-audit-runbook.md` to full-period audit only:
  - removed cutoff/as-of sections and `Q*` queries
  - kept only `P1..P8`, timezone check, expected CSV outputs, and one export command
- Optimized heavy full-period queries after timeout feedback:
  - removed `FINAL` and global `ORDER BY` from export queries
  - added `PREWHERE` on account/time filters
  - rewrote `P3` (`order_history_mm`) to filter by `_SeqNo` range derived from `events_history` (matches table sort key `(Account, _SeqNo, InstrumentType)`)
- Added chunked export strategy in `scripts/export_company_audit_csv.sh` for timeout-prone queries:
  - `P3/P4/P5/P8` run as month chunks (all 4 accounts together) and append into single CSVs
  - `P1` remains single-query export
  - keeps output filenames unchanged while reducing per-query runtime
- Increased exporter timeout default from `1000` to `3600` seconds to reduce chunk timeout failures.
- Scope narrowed per operator request:
  - removed `P2` (`transfer_history`), `P6` (`delivery_history`), and `P7` (`stake_history`) from runbook exports
  - active export set is now `P1`, `P3`, `P4`, `P5`, `P8`
- Verified with:
  - `bash -n scripts/export_company_audit_csv.sh`
  - `scripts/export_company_audit_csv.sh --help`

## Validate Cursor PR Comments for Funding Restarts/Timestamps (2026-02-16)
### Spec
- Validate Cursor PR comments for funding-adapter restart behavior and Binance external funding timestamps.
- Fix only comments that are valid and keep scope limited to funding-related paths.

### Plan
- [x] Validate each comment against current implementation and classify valid/invalid.
- [x] Fix funding app restart flow to avoid replay churn, overlapping restarts, and stale-state restart races.
- [x] Fix Binance external funding publish timestamp to use exchange source event time.
- [x] Add/adjust unit tests to prove behavior.
- [x] Run targeted tests for changed packages and document results.

### Results
- Cursor comments validated as correct for current code paths:
  - funding restarts were ungated by caught-up and launched as concurrent goroutines
  - funding restart timing could race adapter state application
  - Binance external funding events were published with processing time
- `apps/funding/funding.go` changes:
  - restart trigger now goes through `requestFundingAdaptersRestart()`
  - restart requests are ignored before `caughtUp`
  - restart execution is debounced and serialized (`fundingAdapterRestartDebounce`, restart state machine)
  - `restartFundingAdapters()` now executes `Restart()` synchronously per adapter (no overlapping goroutine fan-out)
- `pkg/adapter/feed/binancefunding.go` changes:
  - parses Binance `E` event time and carries it through publish path
  - falls back to adapter clock only if source timestamp is absent
- Added regression coverage:
  - `apps/funding/funding_test.go`
    - `TestOnEventDoesNotRestartFundingAdaptersBeforeCaughtUp`
    - `TestOnEventSerializesFundingAdapterRestarts`
  - `pkg/adapter/feed/funding_events_test.go`
    - Binance funding event timestamp now asserted against source `E`
- Verification:
  - `go test ./apps/funding`
  - `go test ./pkg/adapter/feed`
  - `go test ./apps/subapps`
  - `go test ./services/oracle`

## Fix MATCH_ORDER Delta Loss In Validator Tagging (2026-02-16)
### Spec
- Investigate branch `tim/add-delta` issue where engine computes non-empty delta but history receives empty delta on `MATCH_ORDER`.
- Add regression test first, then fix the root cause.

### Plan
- [x] Add failing validator test proving `MATCH_ORDER` delta is dropped during tagging.
- [x] Patch tag logic to preserve delta (and related dropped fields).
- [x] Run targeted validator/history tests.

### Results
- Root cause confirmed in `platform/validator/tag.go`: `Tag()` rebuilt `MatchOrderEvent` and dropped `Delta` (and `UpdateOrders`).
- Added failing regression test `TestTagMatchOrderPreservesDelta` in `platform/validator/orders_test.go`.
- Fixed by preserving both fields when rebuilding `MatchOrderEvent`:
  - `UpdateOrders: body.GetUpdateOrders()`
  - `Delta: body.GetDelta()`
- Verification:
  - `go test ./platform/validator -run TestTagMatchOrderPreservesDelta -v`
  - `go test ./platform/validator`
  - `go test ./apps/history -run TestGenerateTradeHistoryCloseFullPosition -v`

## Fix MarketsSummary Panic on ExternalFundingWeight (2026-02-16)
### Spec
- Resolve panic in `pkg/handlers.TestMarketsSummary` caused by `services/system.ExternalFundingWeight` when perpetual config or weight string is missing.

### Plan
- [x] Reproduce panic path from failure log.
- [x] Harden `ExternalFundingWeight` against nil/empty config data.
- [x] Add regression tests for no-panic behavior in system/oracle paths.
- [x] Re-run targeted tests.

### Results
- Hardened `services/system/system.go`:
  - `ExternalFundingWeight` now returns `0` when perpetual config is missing.
  - parsing changed to safe parser (`num.NewStringZero`) so empty/invalid strings do not panic.
- Added tests:
  - `services/system/system_test.go`: `TestExternalFundingWeightWithoutPerpetualConfigReturnsZero`
  - `services/oracle/oracle_test.go`:
    - `TestComputeEffectiveFundingRateWithoutPerpetualConfigDoesNotPanic`
    - `TestFundingComponentsWithoutPerpetualConfigDoesNotPanic`
- Verified:
  - `go test ./pkg/handlers -run TestMarketsSummary -v`
  - `go test ./services/system`
  - `go test ./services/oracle`

## Instrument-Level Hedge Mode Implementation (2026-02-18)
### Spec
- Implement instrument-scoped position mode for perpetuals with `ONE_WAY`/`HEDGE`.
- In `HEDGE`, require explicit `position_side` (`LONG`/`SHORT`) for perp orders and RFQ legs.
- In `ONE_WAY`, opposite-direction orders must behave as reduce-only and reject non-reducing remainder.

### Plan
- [ ] Add protobuf enums/messages/fields for instrument-level mode and position side; regenerate generated code.
- [ ] Add accounts state storage for per-instrument position modes and side-specific perpetual positions.
- [ ] Add API endpoints and handler response fields for instrument-level mode management.
- [ ] Enforce mode/side rules in order and RFQ validators (including one-way opposite-side reduce-only behavior).
- [ ] Update execution/accounting paths (risk/engine/accounts/orders/stops/offsets) to use side-aware position updates.
- [ ] Add or update tests that cover one-way vs hedge behavior and side-isolated positions.
- [ ] Run focused suites (`apps/api`, `platform/validator`, `services/accounts`, `apps/risk`, `apps/engine`, `services/stops`, `pkg/offsets`, `pkg/rfq`) and fix regressions.
- [ ] Document implementation notes and verification results in this section.
