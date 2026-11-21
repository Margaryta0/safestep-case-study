"""
SafeStep — відтворювана економічна модель (ЛР 2, 4, 5, 6 з «Економіки ПЗ»).

Скрипт з нуля перераховує ключові числа звітів і порівнює їх зі значеннями,
наведеними у звітах. Запуск:  python model/safestep_model.py
Потрібен лише Python 3.9+, сторонніх бібліотек немає.
"""
from math import sqrt

# --------------------------------------------------------------------------
# ЛР 2. PERT: мережа робіт, критичний шлях, P50/P80
# --------------------------------------------------------------------------
# id: (O, M, P, [попередники])  — з таблиць 2 і А1 звіту ЛР 2
WBS = {
    "1.1": (4, 7, 12, []),
    "1.2": (6, 10, 20, ["1.1"]),
    "2.1": (5, 8, 14, ["1.1"]),
    "2.2": (6, 10, 18, ["2.1"]),
    "2.3": (20, 28, 45, ["1.1"]),
    "3.1": (8, 12, 20, ["2.2"]),
    "3.2": (10, 15, 26, ["2.2"]),
    "3.3": (10, 15, 26, ["3.1", "3.2"]),
    "3.4": (8, 14, 30, ["3.3"]),
    "3.5": (10, 15, 24, ["3.2", "2.3"]),
    "3.6": (7, 11, 20, ["3.2", "3.4"]),
    "3.8": (10, 18, 38, ["3.5"]),
    "3.7": (5, 8, 14, ["3.2", "1.2", "3.8"]),
    "4.1": (12, 18, 30, ["2.3"]),
    "4.2": (8, 14, 35, ["4.1", "3.5"]),
    "5.1": (10, 15, 28, ["3.4", "3.6", "3.7", "3.8"]),
    "5.2": (6, 10, 18, ["3.4", "3.6", "3.7", "3.8"]),
    "5.3": (8, 12, 22, ["5.1"]),
    "5.4": (3, 6, 12, ["5.3", "5.2", "4.2"]),
}


def pert():
    E = {k: (o + 4 * m + p) / 6 for k, (o, m, p, _) in WBS.items()}
    V = {k: ((p - o) / 6) ** 2 for k, (o, m, p, _) in WBS.items()}
    ES, EF = {}, {}
    for k in WBS:  # словник уже впорядковано топологічно
        ES[k] = max((EF[d] for d in WBS[k][3]), default=0.0)
        EF[k] = ES[k] + E[k]
    end = max(EF.values())
    LF = {k: end for k in WBS}
    for k in reversed(list(WBS)):
        succ = [s for s in WBS if k in WBS[s][3]]
        if succ:
            LF[k] = min(LF[s] - E[s] for s in succ)
    crit = [k for k in WBS if abs(LF[k] - EF[k]) < 1e-6]
    sigma = sqrt(sum(V[k] for k in crit))
    return end, crit, sigma, {k: LF[k] - EF[k] for k in WBS}


# --------------------------------------------------------------------------
# ЛР 2. UCP
# --------------------------------------------------------------------------
def ucp():
    uaw = 2 * 1 + 3 * 2 + 1 * 3
    uucw = 4 * 5 + 4 * 10 + 2 * 15
    u = (uaw + uucw) * 0.95 * 0.87
    return u, u * 24


# --------------------------------------------------------------------------
# ЛР 4. Тарифна сітка і gross margin (масштаб третього року)
# --------------------------------------------------------------------------
TIERS = {  # клієнтів, ціна €/міс., середнє usage (учнів), вага підтримки
    "Basic": (40, 209, 20, 1),
    "Standard": (16, 649, 80, 2),
    "Pro": (4, 2290, 330, 4),
}
COGS_UNIT = 1.70
SUPPORT_POOL = 1990


def pricing():
    w = sum(n * wt for n, _, _, wt in TIERS.values())
    revenue = sum(n * price for n, price, _, _ in TIERS.values())
    units = sum(n * u for n, _, u, _ in TIERS.values())
    cogs = units * COGS_UNIT + SUPPORT_POOL
    per_tier = {}
    for t, (n, price, u, wt) in TIERS.items():
        c = u * COGS_UNIT + SUPPORT_POOL / w * wt
        per_tier[t] = 1 - c / price
    return revenue, units, cogs, per_tier


# --------------------------------------------------------------------------
# ЛР 5. Unit economics і break-even
# --------------------------------------------------------------------------
ACQ_SPEND, NEW_PER_MONTH, CHURN, FIXED_OPEX, OTHER_VAR = 6800, 170, 0.06, 13000, 0.05


def unit_economics():
    revenue, units, cogs, _ = pricing()
    arpu = revenue / units
    gm = (revenue - cogs) / revenue
    cac = ACQ_SPEND / NEW_PER_MONTH
    cm = arpu - cogs / units - OTHER_VAR * arpu
    ltv = arpu * gm / CHURN
    base, history = 0.0, []
    for _ in range(12):
        base = base * (1 - CHURN) + NEW_PER_MONTH
        history.append(base)
    return dict(
        arpu=arpu, gm=gm, cac=cac, cm=cm, ltv=ltv, ltv_cac=ltv / cac,
        payback=cac / (arpu * gm),
        be_product=FIXED_OPEX / cm, be_operating=(FIXED_OPEX + ACQ_SPEND) / cm,
        steady_base=NEW_PER_MONTH / CHURN, base_m12=history[-1],
    )


# --------------------------------------------------------------------------
# ЛР 6. Квартальний cash flow і NPV
# --------------------------------------------------------------------------
CF0, RATE = 220_000, 0.24


def cash_flow(price_mult=1.0, inflow_mult=1.0, outflow_mult=1.0, rate=RATE):
    revenue, units, cogs, _ = pricing()
    arpu, cogs_unit = revenue / units * price_mult, cogs / units
    base, months = 0.0, []
    for _ in range(36):
        base = base * (1 - CHURN) + NEW_PER_MONTH
        months.append(base)
    rq = (1 + rate) ** 0.25 - 1
    npv, cum, prev_rev, total_in, total_out = -CF0, -CF0, 0.0, 0.0, CF0
    for q in range(12):
        learner_months = sum(months[3 * q:3 * q + 3])
        rev = learner_months * arpu
        inflow = (0.9 * rev + 0.1 * prev_rev) * inflow_mult   # A4: 10% надходить наступного кварталу
        fixed = 3 * (FIXED_OPEX + ACQ_SPEND) * 1.01 ** q       # A5: +1% за квартал
        outflow = (learner_months * cogs_unit + OTHER_VAR * rev + fixed) * outflow_mult
        net = inflow - outflow
        npv += net / (1 + rq) ** (q + 1)
        cum += net
        total_in += inflow
        total_out += outflow
        prev_rev = rev
    return dict(npv=npv, cum_q12=cum, inflows=total_in, roi=(total_in - total_out) / total_out)


# --------------------------------------------------------------------------
def check(name, got, expected, tol):
    ok = abs(got - expected) <= tol
    print(f"  {'OK ' if ok else 'ERR'} {name:<38} модель {got:>14,.2f}   звіт {expected:>14,.2f}")
    return ok


def main():
    res = []
    print("ЛР 2 — строк і трудомісткість")
    end, crit, sigma, slack = pert()
    res += [check("Критичний шлях μ, роб. дні", end, 122.5, 0.05),
            check("σ критичного шляху, дні", sigma, 7.83, 0.01),
            check("P80 = μ + 0,842σ, дні", end + 0.842 * sigma, 129.1, 0.05),
            check("Запас гілки Dev A (3.4), дні", slack["3.4"], 0.7, 0.05)]
    print("    критичний шлях:", " → ".join(crit))
    u, effort = ucp()
    res += [check("UCP", u, 83.48, 0.01), check("Effort UCP, люд.-год", effort, 2003.4, 0.1)]

    print("ЛР 4 — монетизація")
    revenue, units, cogs, tiers = pricing()
    res += [check("Revenue Y3, €/міс.", revenue, 27_904, 0.5),
            check("COGS Y3, €/міс.", cogs, 7_770, 0.5),
            check("GM Basic, %", tiers["Basic"] * 100, 72.9, 0.05),
            check("GM Pro, %", tiers["Pro"] * 100, 71.6, 0.05)]

    print("ЛР 5 — unit economics")
    ue = unit_economics()
    res += [check("ARPU, €", ue["arpu"], 8.21, 0.005),
            check("CAC, €", ue["cac"], 40.0, 0.001),
            check("LTV, €", ue["ltv"], 98.70, 0.05),
            check("LTV/CAC", ue["ltv_cac"], 2.47, 0.005),
            check("CAC payback, міс.", ue["payback"], 6.8, 0.05),
            check("Product break-even, учнів", ue["be_product"], 2_359, 1),
            check("Operating break-even, учнів", ue["be_operating"], 3_593, 1),
            check("База на 12-му місяці, учнів", ue["base_m12"], 1_485, 1)]

    print("ЛР 6 — NPV (r = 24%, 12 кварталів)")
    base = cash_flow()
    res += [check("NPV Base, €", base["npv"], -532_605, 300),
            check("Cumulative CF Q12, €", base["cum_q12"], -635_625, 300),
            check("NPV Optimistic, €", cash_flow(inflow_mult=1.15)["npv"], -482_152, 300),
            check("NPV Pessimistic, €", cash_flow(inflow_mult=0.8, outflow_mult=1.1)["npv"], -664_772, 300)]

    # ЛР 6/8: за якої ціни NPV = 0 (NPV лінійний за ціною)
    a, b = cash_flow(1.0)["npv"], cash_flow(2.0)["npv"]
    mult = 1 - a / (b - a)
    print(f"  ..  NPV = 0 при ARPU ≈ {ue['arpu'] * mult:.2f} € (×{mult:.2f})  — у звіті ЛР 8: 21,90 € (×2,67)")

    print(f"\n{sum(res)}/{len(res)} показників збігаються зі звітами")
    return all(res)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
