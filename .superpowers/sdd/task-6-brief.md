# Task 6: F&O Scoring Engine (TestableScorer)

## Files
- Create: `breakoutstocks/scanners/fo_scorer.py`
- Create: `tests/test_scorer.py`

## Interfaces
- Consumes: `Config` (from `breakoutstocks.config`), `Advice`, `Confidence`, `TradePlan`, `StockAnalysis` (from `breakoutstocks.models.types`)
- Produces: `TestableScorer` with methods:
  - `__init__(config: Optional[Config] = None)`
  - `calculate_cash_score(row: pd.Series) -> float` (0-20 pts)
  - `calculate_price_score(row: pd.Series) -> float` (0-20 pts)
  - `calculate_delivery_score(row: pd.Series) -> float` (0-10 pts)
  - `calculate_futures_score(row: pd.Series) -> float` (0-15 pts)
  - `calculate_options_score(row: pd.Series) -> float` (0-20 pts)
  - `calculate_market_score(row: pd.Series) -> float` (0-10 pts)
  - `calculate_risk_penalty(row: pd.Series) -> float` (0-15 pts deducted)
  - `calculate_final_score(row: pd.Series) -> float` (clamped 0-100)
  - `generate_advice(row: pd.Series) -> Tuple[Advice, List[str]]` (evaluates hard vetoes like F&O ban, earnings event, extreme IV, and score tiers)
  - `generate_trade_plan(row: pd.Series, advice: Advice) -> Optional[TradePlan]` (computes entry, stop_loss, target_1, target_2, risk_reward, position_size, invalidation)
  - `generate_reasons(row: pd.Series) -> List[str]` (produces technical thesis bullet points)
  - `determine_confidence(row: pd.Series, advice: Advice, warnings: List[str]) -> Confidence` (HIGH, MEDIUM, LOW)
  - `analyze_stock(row: pd.Series) -> StockAnalysis` (full analysis pipeline)

## Global Constraints
- Python 3.10+ required
- Must pass all 10 unit tests ported from `nse_fo_consolidated_scanner.py`
- All score constants and thresholds must come from `Config` (no magic numbers inline)
- Score tiers: Strong Buy >= 80, Buy >= 65, Watch >= 50, Wait >= 35, Avoid < 35
- Hard vetoes: F&O ban, earnings within 3 days, extreme IV

## Steps (TDD)
1. Write `tests/test_scorer.py` porting all 10 unit tests from legacy `nse_fo_consolidated_scanner.py`:
   - Test 1: Cash Score
   - Test 2: Price Score
   - Test 3: Options Score
   - Test 4: Risk Penalty
   - Test 5: Final Score Clamping [0, 100]
   - Test 6: Advice Generation (Strong Buy)
   - Test 7: Advice Generation (Avoid on F&O ban)
   - Test 8: Trade Plan Generation
   - Test 9: Confidence Level
   - Test 10: Reasons Generation
2. Run pytest to verify tests fail (RED phase)
3. Implement `breakoutstocks/scanners/fo_scorer.py`
4. Run pytest to verify all 10 tests pass (GREEN phase)
5. Commit with `git add -A` and `git commit -m "feat: port TestableScorer with 10 TDD tests passing"`
