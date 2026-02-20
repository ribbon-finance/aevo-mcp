from __future__ import annotations

from collections.abc import Callable
from mcp.server.fastmcp import FastMCP


def register_options_prompts(mcp: FastMCP) -> dict[str, Callable]:
    @mcp.prompt()
    def options_strategy_selector(
        asset: str = "ETH",
        outlook: str = "neutral",
        volatility_view: str = "high",
    ) -> str:
        outlook_l = outlook.lower()
        vol_l = volatility_view.lower()

        if outlook_l == "bullish":
            strategies = (
                "Recommended strategies for BULLISH outlook:\n"
                "  1. Bull Call Spread — buy lower-strike call, sell higher-strike call.\n"
                "     Risk: limited (net debit). Reward: limited (strike width - debit).\n"
                "     Greek profile: +Delta, mild -Theta, mild +Vega.\n"
                "     Best for: moderate bullish conviction with defined risk.\n"
                "  2. Long Call — buy a call option.\n"
                "     Risk: limited (premium paid). Reward: unlimited.\n"
                "     Greek profile: +Delta, -Theta, +Vega.\n"
                "     Best for: strong bullish conviction, want full upside.\n"
            )
        elif outlook_l == "bearish":
            strategies = (
                "Recommended strategies for BEARISH outlook:\n"
                "  1. Bear Put Spread — buy higher-strike put, sell lower-strike put.\n"
                "     Risk: limited (net debit). Reward: limited (strike width - debit).\n"
                "     Greek profile: -Delta, mild -Theta, mild +Vega.\n"
                "     Best for: moderate bearish conviction with defined risk.\n"
                "  2. Long Put — buy a put option.\n"
                "     Risk: limited (premium paid). Reward: large (price to zero).\n"
                "     Greek profile: -Delta, -Theta, +Vega.\n"
                "     Best for: strong bearish conviction.\n"
            )
        elif vol_l == "high":
            strategies = (
                "Recommended strategies for NEUTRAL + HIGH VOLATILITY:\n"
                "  1. Long Straddle — buy call + put at same strike (ATM).\n"
                "     Risk: limited (total premium). Reward: unlimited.\n"
                "     Greek profile: ~0 Delta, +Gamma, -Theta, +Vega.\n"
                "     Best for: expecting big move, direction unknown.\n"
                "  2. Long Strangle — buy OTM call + OTM put.\n"
                "     Risk: limited (total premium, cheaper than straddle). Reward: unlimited.\n"
                "     Greek profile: ~0 Delta, +Gamma, -Theta, +Vega.\n"
                "     Best for: expecting big move, want cheaper entry.\n"
            )
        else:
            strategies = (
                "Recommended strategies for NEUTRAL + LOW VOLATILITY:\n"
                "  1. Iron Condor — sell OTM put + call, buy further OTM put + call.\n"
                "     Risk: limited (wing width - credit). Reward: limited (net credit).\n"
                "     Greek profile: ~0 Delta, -Gamma, +Theta, -Vega.\n"
                "     Best for: rangebound market, collect premium from time decay.\n"
                "  2. Butterfly Spread — buy 1 lower call, sell 2 middle calls, buy 1 upper call.\n"
                "     Risk: limited (net debit). Reward: limited (middle - lower - debit).\n"
                "     Greek profile: ~0 Delta, varies Gamma, +Theta near expiry, -Vega.\n"
                "     Best for: expecting price to pin near a specific level.\n"
            )

        return (
            "OPTIONS STRATEGY SELECTOR\n"
            f"Asset: {asset}\n"
            f"Outlook: {outlook}\n"
            f"Volatility view: {volatility_view}\n\n"
            f"{strategies}\n"
            "Data-gathering sequence:\n"
            f"1) Fetch spot price via `index_price(asset='{asset}')`.\n"
            f"2) Fetch available expiries via `expiries(asset='{asset}')`.\n"
            f"3) Fetch options chain via `markets(asset='{asset}', instrument_type='OPTION')`.\n"
            "4) Present the above strategies with live premium estimates from `orderbook`.\n"
            "5) Ask user to select a strategy, then use the matching prompt:\n"
            "   - `options_straddle`, `options_strangle`, `options_bull_call_spread`,\n"
            "     `options_bear_put_spread`, `options_iron_condor`, `options_butterfly`.\n\n"
            "INSTRUMENT NAMING: {ASSET}-{DDMMMYY}-{STRIKE}-{C or P}\n"
            "  Example: ETH-28MAR25-3000-C, BTC-28MAR25-70000-P\n"
        )

    @mcp.prompt()
    def options_straddle(
        asset: str = "ETH",
        expiry: str = "",
        strike: str = "",
    ) -> str:
        return (
            "LONG STRADDLE EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'} | Strike: {strike or 'ATM'}\n\n"
            "STRUCTURE: Buy 1 Call + Buy 1 Put at SAME strike and expiry.\n"
            "BIAS: Direction-neutral, profits from large price move either way.\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries: `expiries(asset='{asset}')`.\n"
            f"3) If no strike given, pick ATM (closest to spot price).\n"
            f"4) Construct instrument names:\n"
            f"   Call: {asset}-{{expiry}}-{{strike}}-C\n"
            f"   Put:  {asset}-{{expiry}}-{{strike}}-P\n"
            "5) Fetch orderbook for both legs to get premiums.\n\n"
            "RISK CALCULATION:\n"
            "  Call Premium  = best ask from call orderbook\n"
            "  Put Premium   = best ask from put orderbook\n"
            "  Total Cost    = Call Premium + Put Premium\n"
            "  Max Loss      = Total Cost (if price = strike at expiry)\n"
            "  Max Profit    = Unlimited\n"
            "  Upper Breakeven = Strike + Total Cost\n"
            "  Lower Breakeven = Strike - Total Cost\n\n"
            "GREEK PROFILE: ~0 Delta, +Gamma, -Theta, +Vega\n"
            "  This position loses money daily (theta) but profits from volatility spikes (vega).\n\n"
            "EXECUTION:\n"
            "1) Review risk numbers with user. Confirm they accept max loss.\n"
            f"2) `create_order(instrument='{asset}-{{expiry}}-{{strike}}-C', is_buy=True, amount='1', limit_price='{{call_premium}}')`\n"
            f"3) `create_order(instrument='{asset}-{{expiry}}-{{strike}}-P', is_buy=True, amount='1', limit_price='{{put_premium}}')`\n"
            "4) Verify both fills via `list_orders` and `positions`.\n"
            "5) Monitor via `portfolio` for Greeks.\n"
        )

    @mcp.prompt()
    def options_strangle(
        asset: str = "ETH",
        expiry: str = "",
        call_strike: str = "",
        put_strike: str = "",
    ) -> str:
        return (
            "LONG STRANGLE EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'}\n"
            f"Call strike: {call_strike or 'OTM above spot'} | Put strike: {put_strike or 'OTM below spot'}\n\n"
            "STRUCTURE: Buy 1 OTM Call + Buy 1 OTM Put (different strikes, same expiry).\n"
            "BIAS: Direction-neutral, cheaper than straddle but needs larger move.\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries: `expiries(asset='{asset}')`.\n"
            "3) If no strikes given, pick ~5-10% OTM on each side of spot.\n"
            f"4) Construct instrument names:\n"
            f"   Call: {asset}-{{expiry}}-{{call_strike}}-C\n"
            f"   Put:  {asset}-{{expiry}}-{{put_strike}}-P\n"
            "5) Fetch orderbook for both legs.\n\n"
            "RISK CALCULATION:\n"
            "  Total Cost    = Call Premium + Put Premium\n"
            "  Max Loss      = Total Cost (if price stays between strikes at expiry)\n"
            "  Max Profit    = Unlimited\n"
            "  Upper Breakeven = Call Strike + Total Cost\n"
            "  Lower Breakeven = Put Strike - Total Cost\n\n"
            "GREEK PROFILE: ~0 Delta, +Gamma, -Theta, +Vega\n\n"
            "EXECUTION:\n"
            "1) Review risk numbers with user.\n"
            f"2) `create_order(instrument='{asset}-{{expiry}}-{{call_strike}}-C', is_buy=True, amount='1', limit_price='{{call_premium}}')`\n"
            f"3) `create_order(instrument='{asset}-{{expiry}}-{{put_strike}}-P', is_buy=True, amount='1', limit_price='{{put_premium}}')`\n"
            "4) Verify fills and monitor Greeks.\n"
        )

    @mcp.prompt()
    def options_bull_call_spread(
        asset: str = "ETH",
        expiry: str = "",
        lower_strike: str = "",
        upper_strike: str = "",
    ) -> str:
        return (
            "BULL CALL SPREAD EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'}\n"
            f"Lower strike: {lower_strike or 'ATM or slightly ITM'} | Upper strike: {upper_strike or 'OTM'}\n\n"
            "STRUCTURE: Buy 1 Call at lower strike + Sell 1 Call at upper strike.\n"
            "BIAS: Moderately bullish with capped risk and reward.\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries and chain: `markets(asset='{asset}', instrument_type='OPTION')`.\n"
            "3) Select two call strikes (lower near ATM, upper OTM).\n"
            f"4) Instruments:\n"
            f"   Long:  {asset}-{{expiry}}-{{lower_strike}}-C (BUY)\n"
            f"   Short: {asset}-{{expiry}}-{{upper_strike}}-C (SELL)\n"
            "5) Fetch orderbook for both.\n\n"
            "RISK CALCULATION:\n"
            "  Net Debit  = Long Call Premium - Short Call Premium\n"
            "  Max Loss   = Net Debit\n"
            "  Max Profit = (Upper Strike - Lower Strike) - Net Debit\n"
            "  Breakeven  = Lower Strike + Net Debit\n\n"
            "GREEK PROFILE: +Delta (moderate), mild -Theta, mild +Vega\n\n"
            "EXECUTION:\n"
            "1) Review risk/reward with user.\n"
            f"2) `create_order(instrument='{asset}-{{expiry}}-{{lower_strike}}-C', is_buy=True, amount='1', limit_price='{{long_premium}}')`\n"
            f"3) `create_order(instrument='{asset}-{{expiry}}-{{upper_strike}}-C', is_buy=False, amount='1', limit_price='{{short_premium}}')`\n"
            "4) Verify fills and monitor position.\n"
        )

    @mcp.prompt()
    def options_bear_put_spread(
        asset: str = "ETH",
        expiry: str = "",
        upper_strike: str = "",
        lower_strike: str = "",
    ) -> str:
        return (
            "BEAR PUT SPREAD EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'}\n"
            f"Upper strike: {upper_strike or 'ATM or slightly ITM'} | Lower strike: {lower_strike or 'OTM'}\n\n"
            "STRUCTURE: Buy 1 Put at upper strike + Sell 1 Put at lower strike.\n"
            "BIAS: Moderately bearish with capped risk and reward.\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries and chain: `markets(asset='{asset}', instrument_type='OPTION')`.\n"
            "3) Select two put strikes (upper near ATM, lower OTM).\n"
            f"4) Instruments:\n"
            f"   Long:  {asset}-{{expiry}}-{{upper_strike}}-P (BUY)\n"
            f"   Short: {asset}-{{expiry}}-{{lower_strike}}-P (SELL)\n"
            "5) Fetch orderbook for both.\n\n"
            "RISK CALCULATION:\n"
            "  Net Debit  = Long Put Premium - Short Put Premium\n"
            "  Max Loss   = Net Debit\n"
            "  Max Profit = (Upper Strike - Lower Strike) - Net Debit\n"
            "  Breakeven  = Upper Strike - Net Debit\n\n"
            "GREEK PROFILE: -Delta (moderate), mild -Theta, mild +Vega\n\n"
            "EXECUTION:\n"
            "1) Review risk/reward with user.\n"
            f"2) `create_order(instrument='{asset}-{{expiry}}-{{upper_strike}}-P', is_buy=True, amount='1', limit_price='{{long_premium}}')`\n"
            f"3) `create_order(instrument='{asset}-{{expiry}}-{{lower_strike}}-P', is_buy=False, amount='1', limit_price='{{short_premium}}')`\n"
            "4) Verify fills and monitor position.\n"
        )

    @mcp.prompt()
    def options_iron_condor(
        asset: str = "ETH",
        expiry: str = "",
        put_buy_strike: str = "",
        put_sell_strike: str = "",
        call_sell_strike: str = "",
        call_buy_strike: str = "",
    ) -> str:
        return (
            "Strategy: Iron Condor - IRON CONDOR EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'}\n"
            f"Put wing: Buy {put_buy_strike or 'far OTM'} / Sell {put_sell_strike or 'OTM'}\n"
            f"Call wing: Sell {call_sell_strike or 'OTM'} / Buy {call_buy_strike or 'far OTM'}\n\n"
            "STRUCTURE: 4 legs — Buy OTM Put, Sell Put, Sell Call, Buy OTM Call.\n"
            "BIAS: Neutral, profits from price staying in range (low volatility).\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries and chain: `markets(asset='{asset}', instrument_type='OPTION')`.\n"
            "3) Select 4 strikes: 2 puts below spot, 2 calls above spot.\n"
            "   Tip: equal wing widths (e.g. 5% apart) for symmetric risk.\n"
            f"4) Instruments (ordered by strike):\n"
            f"   {asset}-{{expiry}}-{{put_buy_strike}}-P   (BUY  — protection)\n"
            f"   {asset}-{{expiry}}-{{put_sell_strike}}-P   (SELL — income)\n"
            f"   {asset}-{{expiry}}-{{call_sell_strike}}-C  (SELL — income)\n"
            f"   {asset}-{{expiry}}-{{call_buy_strike}}-C   (BUY  — protection)\n"
            "5) Fetch orderbook for all 4 legs.\n\n"
            "RISK CALCULATION:\n"
            "  Net Credit    = (Put Sell Premium + Call Sell Premium)\n"
            "                  - (Put Buy Premium + Call Buy Premium)\n"
            "  Max Profit    = Net Credit (if price stays between sell strikes at expiry)\n"
            "  Wing Width    = Put Sell Strike - Put Buy Strike (or Call Buy - Call Sell)\n"
            "  Max Loss      = Wing Width - Net Credit\n"
            "  Lower Breakeven = Put Sell Strike - Net Credit\n"
            "  Upper Breakeven = Call Sell Strike + Net Credit\n\n"
            "GREEK PROFILE: ~0 Delta, -Gamma, +Theta, -Vega\n"
            "  This position earns money daily (theta) but loses if volatility spikes (vega).\n\n"
            "EXECUTION:\n"
            "1) Review risk numbers with user. Confirm max loss is acceptable.\n"
            "2) Execute all 4 legs:\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{put_buy_strike}}-P', is_buy=True, amount='1', limit_price='...')`\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{put_sell_strike}}-P', is_buy=False, amount='1', limit_price='...')`\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{call_sell_strike}}-C', is_buy=False, amount='1', limit_price='...')`\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{call_buy_strike}}-C', is_buy=True, amount='1', limit_price='...')`\n"
            "3) Verify all fills. If partial, consider closing unfilled legs.\n"
            "4) Monitor via `positions` and `portfolio` for Greeks.\n"
        )

    @mcp.prompt()
    def options_butterfly(
        asset: str = "ETH",
        expiry: str = "",
        lower_strike: str = "",
        middle_strike: str = "",
        upper_strike: str = "",
    ) -> str:
        return (
            "Strategy: Butterfly Spread - BUTTERFLY SPREAD EXECUTION PLAN\n"
            f"Asset: {asset} | Expiry: {expiry or 'TBD'}\n"
            f"Lower: {lower_strike or 'TBD'} | Middle: {middle_strike or 'ATM'} | Upper: {upper_strike or 'TBD'}\n\n"
            "STRUCTURE: Buy 1 Call lower, Sell 2 Calls middle, Buy 1 Call upper.\n"
            "  Strikes must be equidistant: middle - lower = upper - middle.\n"
            "BIAS: Neutral, profits if price pins near middle strike at expiry.\n\n"
            "Data gathering:\n"
            f"1) Fetch spot: `index_price(asset='{asset}')`.\n"
            f"2) Fetch expiries and chain: `markets(asset='{asset}', instrument_type='OPTION')`.\n"
            "3) If no strikes given, pick middle = ATM, then lower/upper equidistant.\n"
            "   Tip: use available strike spacing from the options chain.\n"
            f"4) Instruments:\n"
            f"   {asset}-{{expiry}}-{{lower_strike}}-C   (BUY  x1)\n"
            f"   {asset}-{{expiry}}-{{middle_strike}}-C  (SELL x2)\n"
            f"   {asset}-{{expiry}}-{{upper_strike}}-C   (BUY  x1)\n"
            "5) Fetch orderbook for all 3 strikes.\n\n"
            "RISK CALCULATION:\n"
            "  Net Debit     = Lower Call Premium + Upper Call Premium\n"
            "                  - (2 x Middle Call Premium)\n"
            "  Max Loss      = Net Debit (if price <= lower or >= upper at expiry)\n"
            "  Max Profit    = (Middle Strike - Lower Strike) - Net Debit\n"
            "                  (occurs when price = middle strike at expiry)\n"
            "  Lower Breakeven = Lower Strike + Net Debit\n"
            "  Upper Breakeven = Upper Strike - Net Debit\n\n"
            "GREEK PROFILE: ~0 Delta, varies Gamma, +Theta near expiry, -Vega\n\n"
            "EXECUTION:\n"
            "1) Review risk numbers with user.\n"
            "2) Execute all 3 legs:\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{lower_strike}}-C', is_buy=True, amount='1', limit_price='...')`\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{middle_strike}}-C', is_buy=False, amount='2', limit_price='...')`\n"
            f"   `create_order(instrument='{asset}-{{expiry}}-{{upper_strike}}-C', is_buy=True, amount='1', limit_price='...')`\n"
            "3) Verify all fills.\n"
            "4) Monitor via `positions` and `portfolio`.\n"
        )

    return {
        "options_strategy_selector": options_strategy_selector,
        "options_straddle": options_straddle,
        "options_strangle": options_strangle,
        "options_bull_call_spread": options_bull_call_spread,
        "options_bear_put_spread": options_bear_put_spread,
        "options_iron_condor": options_iron_condor,
        "options_butterfly": options_butterfly,
    }
