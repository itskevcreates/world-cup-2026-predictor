# Prediction Model — Design & Methodology

## 1. Why the old model overrated Argentina (exact diagnosis)

The previous rating was `strength = learned_Elo + form_adjustment`, then fed to a Poisson
scoreline model and a Monte Carlo. Every term that decided the title favourite was a
**pre-tournament prior**:

| Cause | Mechanism | Mathematical effect on Argentina |
|------|-----------|----------------------------------|
| 1. Elo *is* reputation | Learned Elo (2138) is the single largest input | Argentina starts ~+150 Elo clear of the field before a ball is kicked |
| 2. Form term too small & capped | `form_adj ∈ [−55, +55]`, ~2.5 % of a 2150 rating | A team outperforming by +7 GD could not overtake a +2 GD powerhouse |
| 3. Goal difference under-weighted | Form used `gd/played` linearly, no opponent context | Germany's +7 GD ≈ Argentina's +5 GD after capping |
| 4. No opponent adjustment | Beating a weak group = beating a strong one | Argentina's results not discounted for an easy path |
| 5. No dominance signal | 1-0 == 3-0 | Narrow wins inflated reputational sides |
| 6. Exponential Elo→goals | `λ = 1.35·e^{Δ/scale}` with small scale | Elo gaps amplified into large scoreline edges, compounding over 5 KO rounds |
| 7. Knockout compounding | 32→1 single elimination | A small per-match edge → large title-share edge for the top seed |

**Net result:** Argentina ≈ 30 % title share — a reputation artefact, not a 2026 signal.

### The fix, quantified
The rating blends squad talent and priors with a **down-weighted** tournament term, and
adds two adjustments the old model lacked — an **opponent-quality discount** (multiplicative)
and an **injury/availability** correction:

```
power = 0.30·tournament_elo + 0.25·squad + 0.20·elo + 0.15·form + 0.10·historical
        + momentum + injury_adjustment
adj_gd = gd_per_game · (1 + 0.55·SOS_z)        # beating weak groups counts for far less
```

Two consequences that fix the bias:
- **Reputation no longer auto-wins, but neither does a soft schedule.** Tournament weight is
  only 30 %, so a powerhouse is not buried by a quiet group stage, *and* a team feasting on
  weak opponents (high raw GD, negative `SOS_z`) has that margin scaled down before it
  counts. Germany's +7 GD against a weak group is discounted and it falls to ~5th.
- **Availability matters.** Spain underperformed with Lamine Yamal absent; an
  `injury_adjustment` forgives part of that, so its rating reflects the fully-fit squad.

Resulting order: **France, Argentina, Spain, Brazil, Germany …** with hosts USA/Mexico
correctly mid-pack rather than top-five, and no single runaway favourite (France ~15 %).

## 2. Dynamic Power Rating (per team, Elo-equivalent units)

```
weights         = tournament .30 · squad .25 · elo .20 · form .15 · historical .10
tournament_elo  = MEAN_ELO + TOURN_SPREAD · z(tournament_score)
tournament_score= 1.00·(ppg − 1) + 0.85·adj_gd + 0.55·dominance + 0.40·over_perf
adj_gd          = gd_per_game · (1 + 0.55·SOS_z)         # multiplicative opponent quality
dominance       = sign(gd)·ln(1+|gd|)                    # diminishing returns; uses xG when fed
over_perf       = (ppg − expected_ppg) · (1 + 0.4·SOS_z) # momentum, opponent-discounted
momentum_bonus  = MOMENTUM_SPREAD · tanh(z(over_perf))
power           = Σ weights·components + momentum_bonus + injury_adjustment
```

- **MEAN_ELO=1750, TOURN_SPREAD=160, MOMENTUM_SPREAD=35.**
- **squad** = real squad-talent ratings (`SQUAD_TALENT`), not an Elo proxy — so deep-talent
  sides (Brazil, France) are valued for their class even after a soft group stage.
- **Strength of schedule (multiplicative):** `SOS_z` = z-score of opponents' mean base Elo
  within the group. Goals piled up against a weak group are scaled *down*; the same margin
  against a strong group is scaled *up*. The same discount is applied to momentum.
- **injury_adjustment:** forgives current underperformance caused by a key absence (e.g.
  Spain w/o Lamine Yamal), so the rating reflects the fully-fit squad.
- **Dominance:** concave in goal difference, so 6-0 ≠ 6×(1-0). When an advanced-stats feed
  populates `MatchStats` (xG, shots, possession, big chances), dominance blends
  `0.45·gd + 0.30·xG_diff + 0.15·big_chance_diff + 0.10·possession` — a 1-0 win while
  out-xG'd scores *lower* than a 3-0 win dominating every metric. Until then it falls back
  to the goal-based proxy (identical code path).

### Outputs per team
`power`, `attack`, `defense`, `momentum`, `schedule_strength`, plus the simulation's
`advance / quarter / semi / final / title` probabilities.

> **Honesty note.** `attack`/`defense` are *estimates*: with only goal **difference**
> available (no GF/GA or xG feed) they cannot be measured independently, so they are split
> with a documented prior (stronger attacking sides score more for the same GD). Connect a
> stats feed and they become real measurements with no code change.

## 3. Advanced features — wired, pending a feed

`MatchStats` already accepts: xG, xGA, shots, shots on target, possession, big chances
created/allowed. The dominance function consumes them when present. **We do not fabricate
these values** — they are `None` until a real provider (Opta/StatsBomb/FBref) is connected.
Squad value / injuries / suspensions are represented by the `squad` prior (Elo-percentile
proxy) and can be replaced by a real squad-value table the same way.

## 4. Monte Carlo simulation

- **100,000+ runs** (`/simulate?n=100000`, 100k ≈ 5 s).
- Each run: finish the remaining group games → rank (top 2 + 8 best thirds, the real 2026
  format) → 32-team single elimination.
- Match outcomes drawn from **Poisson scorelines** whose λ comes from the **power ratings**
  (not Elo), so momentum/SOS/dominance flow into every simulated game.
- Knockout ties resolved by a power-weighted ET/penalty coin.
- Aggregates give round-by-round probabilities for all teams.

## 5. Validation (`pipelines/validate.py`, run on 8,152 held-out 2018+ matches)

| Metric | Value | Meaning |
|--------|-------|---------|
| Accuracy | 0.600 | vs 0.478 most-common baseline |
| Log loss | 0.873 | penalises confident wrong calls |
| Brier (multiclass) | 0.513 | MSE of the probability vector |
| Brier (home) | 0.187 | one-vs-rest home-win |
| **Calibration** | near-diagonal | of matches called ~70 % home, 76 % were home |

- **Calibration curve:** bucket predictions by probability, compare to observed frequency;
  a good model sits on the diagonal (ours does).
- **Backtesting:** restrict the held-out set to `tournament == 'FIFA World Cup'`, dates
  2018/2022, and re-score — measures tournament-specific skill rather than all friendlies.
- **Time-based split only:** training never sees matches after the test cut, so there is no
  look-ahead leakage.
