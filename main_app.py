import pandas as pd

# ===== STRATEGY 1 =====
def put_sell_signal(chain_df, current_price, am_price):
    """
    Strategy:
    If market falls >1% from 5:29 AM price,
    find an OTM put in $270-$330 range and return signal for selling 23 lots.
    """
    pct_change = ((current_price - am_price) / am_price) * 100

    if pct_change <= -1:  # Market dropped more than 1%
        otm_puts = chain_df[
            (chain_df['Strike'] < current_price) &
            (chain_df['Put_Price'] >= 270) &
            (chain_df['Put_Price'] <= 330)
        ][['Strike', 'Put_Symbol', 'Put_Price']]

        if not otm_puts.empty:
            otm_puts['distance'] = abs(otm_puts['Strike'] - current_price)
            best_put = otm_puts.sort_values(by='distance').iloc[0]
            total_notional = best_put['Put_Price'] * 23  # 23 lots

            return {
                "signal": f"📉 Market fell {pct_change:.2f}% → SELL PUT {best_put['Strike']} @ ${best_put['Put_Price']:.2f} for 23 lots (~${total_notional:,.2f} notional)",
                "details": best_put.to_dict()
            }
        else:
            return {
                "signal": "📉 Market fell >1%, but no matching OTM puts found in $270–$330 range.",
                "details": None
            }
    else:
        return {
            "signal": f"✅ Market drop only {pct_change:.2f}%, no sell signal.",
            "details": None
        }

# ===== STRATEGY 2 =====
def otm_filter_100_200(chain_df, current_price, am_price):
    """
    Strategy:
    Show OTM calls & puts between $100 and $200 mark price.
    """
    otm_calls = chain_df[
        (chain_df['Strike'] > current_price) &
        (chain_df['Call_Price'] >= 100) &
        (chain_df['Call_Price'] <= 200)
    ][['Strike', 'Call_Symbol', 'Call_Price']]

    otm_puts = chain_df[
        (chain_df['Strike'] < current_price) &
        (chain_df['Put_Price'] >= 100) &
        (chain_df['Put_Price'] <= 200)
    ][['Strike', 'Put_Symbol', 'Put_Price']]

    return {
        "signal": f"📊 Found {len(otm_calls)} OTM Calls and {len(otm_puts)} OTM Puts in $100–$200 range.",
        "details": pd.concat([otm_calls, otm_puts], keys=['Calls', 'Puts']).reset_index(level=0).rename(columns={'level_0': 'Type'})
    }

# ===== STRATEGY REGISTRY =====
strategies = {
    "Sell OTM Put if BTC falls >1% (270-330 range)": put_sell_signal,
    "OTM Calls & Puts in $100-200 range": otm_filter_100_200
}

# ===== STRATEGY RUNNER =====
def run_strategy(chain_df, current_price, am_price, selected_strategy=None):
    """
    Runs the selected strategy from the registry.
    """
    if selected_strategy is None:
        selected_strategy = list(strategies.keys())[0]  # Default to first

    strategy_func = strategies.get(selected_strategy)
    if strategy_func:
        return strategy_func(chain_df, current_price, am_price)
    else:
        return {"signal": "❌ Strategy not found.", "details": None}
