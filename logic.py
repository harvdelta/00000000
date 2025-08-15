def filter_put_sell_signal(chain_df, current_price, am_price):
    """
    Strategy:
    If market falls >1% from 5:29 AM price,
    find an OTM put in $270-$330 range and return signal for selling 23 lots.
    """
    # Calculate % change from 5:29 AM price
    pct_change = ((current_price - am_price) / am_price) * 100

    # Check condition
    if pct_change <= -1:  # Market dropped more than 1%
        # Filter OTM puts in desired price range
        otm_puts = chain_df[
            (chain_df['Strike'] < current_price) &
            (chain_df['Put_Price'] >= 270) &
            (chain_df['Put_Price'] <= 330)
        ][['Strike', 'Put_Symbol', 'Put_Price']]

        if not otm_puts.empty:
            # Select put closest to ATM
            otm_puts['distance'] = abs(otm_puts['Strike'] - current_price)
            best_put = otm_puts.sort_values(by='distance').iloc[0]

            # Assume 1 lot = 1 BTC contract
            contract_price = best_put['Put_Price']
            total_notional = contract_price * 23  # 23 lots

            return {
                "signal": f"📉 Market fell {pct_change:.2f}% → SELL PUT {best_put['Strike']} @ ${contract_price:.2f} for 23 lots (~${total_notional:,.2f} notional)",
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
