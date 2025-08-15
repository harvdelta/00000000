def filter_otm_100_200(chain_df, current_price):
    """Filter OTM calls and puts between $100 and $200 mark price."""
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

    return otm_calls, otm_puts
