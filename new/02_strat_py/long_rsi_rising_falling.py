import numpy as np
import plotly.graph_objects as go
from logging import getLogger
from typing import NamedTuple
from os.path import join, abspath
from quantfreedom.helpers.helper_funcs import np_lookback_one
from quantfreedom.indicators.tv_indicators import rsi_tv
from quantfreedom.core.strategy import Strategy
from quantfreedom.core.enums import (
    BacktestSettings,
    CandleBodyType,
    DynamicOrderSettings,
    ExchangeSettings,
    FootprintCandlesTuple,
    IncreasePositionType,
    LeverageStrategyType,
    StaticOrderSettings,
    StopLossStrategyType,
    TakeProfitStrategyType,
)

logger = getLogger()


class IndicatorSettings(NamedTuple):
    rsi_length: np.ndarray
    above_rsi_cur: np.ndarray
    above_rsi_p: np.ndarray
    above_rsi_pp: np.ndarray
    below_rsi_cur: np.ndarray
    below_rsi_p: np.ndarray
    below_rsi_pp: np.ndarray


class RSIRisingFalling(Strategy):
    og_ind_set_tuple: IndicatorSettings
    cur_ind_set_tuple: IndicatorSettings

    def __init__(
        self,
        long_short: str,
        shuffle_bool: bool,
        rsi_length: np.ndarray,
        above_rsi_cur: np.ndarray = np.array([0]),
        above_rsi_p: np.ndarray = np.array([0]),
        above_rsi_pp: np.ndarray = np.array([0]),
        below_rsi_cur: np.ndarray = np.array([0]),
        below_rsi_p: np.ndarray = np.array([0]),
        below_rsi_pp: np.ndarray = np.array([0]),
    ) -> None:

        self.long_short = long_short
        self.log_folder = abspath(join(abspath(""), ".."))
        self.exchange_settings_tuple = exchange_settings_tuple
        self.backtest_settings_tuple = backtest_settings_tuple

        og_ind_set_tuple = IndicatorSettings(
            rsi_length=rsi_length,
            above_rsi_cur=above_rsi_cur,
            above_rsi_p=above_rsi_p,
            above_rsi_pp=above_rsi_pp,
            below_rsi_cur=below_rsi_cur,
            below_rsi_p=below_rsi_p,
            below_rsi_pp=below_rsi_pp,
        )

        if long_short == "long":
            og_dos_tuple = long_og_dos_tuple
            self.chart_title = "Long Signal"
            self.entry_message = self.long_entry_message
            self.live_bt = self.long_live_bt
            self.live_evaluate = self.long_live_evaluate
            self.set_cur_ind_tuple = self.long_set_cur_ind_tuple
            self.set_entries_exits_array = self.long_set_entries_exits_array
            self.set_live_bt_entries_exits_array = self.long_live_bt_set_entries_exits_array
            self.static_os_tuple = long_static_os_tuple
        else:
            og_dos_tuple = None
            self.chart_title = "short Signal"
            self.entry_message = self.short_entry_message
            self.live_bt = self.short_live_bt
            self.live_evaluate = self.short_live_evaluate
            self.set_cur_ind_tuple = self.short_set_cur_ind_tuple
            self.set_entries_exits_array = self.short_set_entries_exits_array
            self.set_live_bt_entries_exits_array = self.short_live_bt_set_entries_exits_array
            self.static_os_tuple = None

        self.set_og_ind_and_dos_tuples(
            og_dos_tuple=og_dos_tuple,
            og_ind_set_tuple=og_ind_set_tuple,
            shuffle_bool=shuffle_bool,
        )

    #######################################################
    #######################################################
    #######################################################
    ##################      Utils     #####################
    ##################      Utils     #####################
    ##################      Utils     #####################
    #######################################################
    #######################################################
    #######################################################

    def set_og_ind_and_dos_tuples(
        self,
        og_dos_tuple: DynamicOrderSettings,
        og_ind_set_tuple: IndicatorSettings,
        shuffle_bool: bool,
    ) -> None:

        cart_prod_array = self.get_ind_set_dos_cart_product(
            og_dos_tuple=og_dos_tuple,
            og_ind_set_tuple=og_ind_set_tuple,
        )

        filtered_cart_prod_array = self.get_filter_cart_prod_array(
            cart_prod_array=cart_prod_array,
        )

        if shuffle_bool:
            final_cart_prod_array = np.random.default_rng().permutation(filtered_cart_prod_array, axis=1)
        else:
            final_cart_prod_array = filtered_cart_prod_array.copy()

        self.og_dos_tuple = self.get_og_dos_tuple(
            final_cart_prod_array=final_cart_prod_array,
        )

        self.og_ind_set_tuple = self.get_og_ind_set_tuple(
            final_cart_prod_array=final_cart_prod_array,
        )
        self.total_filtered_settings = self.og_ind_set_tuple.rsi_length.size

        logger.debug("set_og_ind_and_dos_tuples")

    def get_og_ind_set_tuple(
        self,
        final_cart_prod_array: np.ndarray,
    ) -> IndicatorSettings:

        ind_set_tuple = IndicatorSettings(*tuple(final_cart_prod_array[12:]))
        logger.debug("ind_set_tuple")

        og_ind_set_tuple = IndicatorSettings(
            rsi_length=ind_set_tuple.rsi_length.astype(np.int_),
            above_rsi_cur=ind_set_tuple.above_rsi_cur.astype(np.int_),
            above_rsi_p=ind_set_tuple.above_rsi_p.astype(np.int_),
            above_rsi_pp=ind_set_tuple.above_rsi_pp.astype(np.int_),
            below_rsi_cur=ind_set_tuple.below_rsi_cur.astype(np.int_),
            below_rsi_p=ind_set_tuple.below_rsi_p.astype(np.int_),
            below_rsi_pp=ind_set_tuple.below_rsi_pp.astype(np.int_),
        )
        logger.debug("og_ind_set_tuple")

        return og_ind_set_tuple

    def get_filter_cart_prod_array(
        self,
        cart_prod_array: np.ndarray,
    ) -> np.ndarray:
        # cart array indexes
        above_rsi_cur = 13
        above_rsi_p = 14
        above_rsi_pp = 15
        below_rsi_cur = 16
        below_rsi_p = 17
        below_rsi_pp = 18

        above_cur_le_p = cart_prod_array[above_rsi_cur] <= cart_prod_array[above_rsi_p]
        above_pp_le_p = cart_prod_array[above_rsi_pp] <= cart_prod_array[above_rsi_p]

        below_cur_ge_p = cart_prod_array[below_rsi_cur] >= cart_prod_array[below_rsi_p]
        below_pp_ge_p = cart_prod_array[below_rsi_pp] >= cart_prod_array[below_rsi_p]

        filtered_indexes = below_cur_ge_p & below_pp_ge_p & above_cur_le_p & above_pp_le_p

        filtered_cart_prod_array = cart_prod_array[:, filtered_indexes]
        logger.debug(f"cart prod size {cart_prod_array.shape[1]:,}")
        logger.debug(f"filtered cart prod size {filtered_cart_prod_array.shape[1]:,}")
        logger.debug(f"Removed {cart_prod_array.shape[1] -filtered_cart_prod_array.shape[1] }")

        filtered_cart_prod_array[11] = np.arange(filtered_cart_prod_array.shape[1])

        return filtered_cart_prod_array

    #######################################################
    #######################################################
    #######################################################
    ##################      Long     ######################
    ##################      Long     ######################
    ##################      Long     ######################
    #######################################################
    #######################################################
    #######################################################

    def long_set_cur_ind_tuple(
        self,
        set_idx: int,
    ):
        rsi_length = self.og_ind_set_tuple.rsi_length[set_idx]
        below_rsi_cur = self.og_ind_set_tuple.below_rsi_cur[set_idx]
        below_rsi_p = self.og_ind_set_tuple.below_rsi_p[set_idx]
        below_rsi_pp = self.og_ind_set_tuple.below_rsi_pp[set_idx]

        self.h_line = below_rsi_cur

        self.cur_ind_set_tuple = IndicatorSettings(
            rsi_length=rsi_length,
            above_rsi_cur=0,
            above_rsi_p=0,
            above_rsi_pp=0,
            below_rsi_cur=below_rsi_cur,
            below_rsi_p=below_rsi_p,
            below_rsi_pp=below_rsi_pp,
        )
        logger.info(
            f"""
Indicator Settings
Indicator Settings Index= {set_idx}
rsi_length= {rsi_length}
below_rsi_cur= {below_rsi_cur}
below_rsi_p= {below_rsi_p}
below_rsi_pp= {below_rsi_pp}
"""
        )

    def long_entry_message(
        self,
        bar_index: int,
    ):
        logger.info("\n\n")
        logger.info(f"Entry time!!!")

    #######################
    ####### reg BT ########
    ####### reg BT ########
    #######################

    def long_set_entries_exits_array(
        self,
        candles: FootprintCandlesTuple,
    ):
        try:
            rsi = rsi_tv(
                source=candles.candle_close_prices,
                length=self.cur_ind_set_tuple.rsi_length,
            )

            self.rsi = np.around(rsi, 1)
            logger.debug("Created RSI")

            rsi_lb = np_lookback_one(
                arr=self.rsi,
                lookback=2,
                include_current=False,
                fill_value=np.nan,
                fwd_bwd="fwd",
            )

            p_rsi = rsi_lb[:, 0]
            pp_rsi = rsi_lb[:, 1]

            falling = pp_rsi > p_rsi
            rising = self.rsi > p_rsi

            is_below_cur = self.rsi < self.cur_ind_set_tuple.below_rsi_cur
            is_below_p = p_rsi < self.cur_ind_set_tuple.below_rsi_p
            is_below_pp = pp_rsi < self.cur_ind_set_tuple.below_rsi_pp

            self.entries = is_below_cur & is_below_p & is_below_pp & falling & rising

            self.entry_signals = np.where(self.entries, self.rsi, np.nan)

            self.exit_prices = np.full_like(self.rsi, np.nan)

            self.entries[: long_static_os_tuple.starting_bar] = False
            self.entry_signals[: long_static_os_tuple.starting_bar] = np.nan
            self.exit_prices[: long_static_os_tuple.starting_bar] = np.nan

            logger.debug("Created entries exits")
        except Exception as e:
            logger.error(f"Exception long_set_entries_exits_array -> {e}")
            raise Exception(f"Exception long_set_entries_exits_array -> {e}")

    ########################
    ####### live BT ########
    ####### live BT ########
    ########################

    def long_live_bt_set_entries_exits_array(
        self,
        candles: FootprintCandlesTuple,
    ):
        candle_len = candles.candle_asset_volumes.size
        self.entries = np.full(candle_len, False)
        self.exit_prices = np.full(candle_len, np.nan)
        self.entry_signals = np.full(candle_len, np.nan)
        self.rsi = rsi_tv(
            source=candles.candle_close_prices,
            length=self.cur_ind_set_tuple.rsi_length,
        )

    def long_live_bt(
        self,
        beg: int,
        candles: FootprintCandlesTuple,
        end: int,
    ):

        try:
            candles = self.candle_chunk(
                candles=candles,
                beg=beg,
                end=end,
            )

            rsi = rsi_tv(
                source=candles.candle_close_prices,
                length=self.cur_ind_set_tuple.rsi_length,
            )

            rsi = np.around(rsi, 1)
            logger.debug("Created RSI")

            cur_rsi = rsi[-1]
            p_rsi = rsi[-2]
            pp_rsi = rsi[-3]

            falling = pp_rsi > p_rsi
            rising = cur_rsi > p_rsi

            is_below_cur = cur_rsi < self.cur_ind_set_tuple.below_rsi_cur
            is_below_p = p_rsi < self.cur_ind_set_tuple.below_rsi_p
            is_below_pp = pp_rsi < self.cur_ind_set_tuple.below_rsi_pp

            result = is_below_cur & is_below_p & is_below_pp & falling & rising

            if result:
                self.entry_signals[bar_index] = cur_rsi
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Exception long_live_bt -> {e}")
            raise Exception(f"Exception long_live_bt -> {e}")

    #####################
    ####### live ########
    ####### live ########
    #####################

    def long_live_evaluate(
        self,
        candles: FootprintCandlesTuple,
    ):

        try:
            rsi = rsi_tv(
                source=candles.candle_close_prices,
                length=self.cur_ind_set_tuple.rsi_length,
            )

            rsi = np.around(rsi, 1)
            logger.debug("Created RSI")

            cur_rsi = rsi[-1]
            p_rsi = rsi[-2]
            pp_rsi = rsi[-3]

            falling = pp_rsi > p_rsi
            rising = cur_rsi > p_rsi

            is_below_cur = cur_rsi < self.cur_ind_set_tuple.below_rsi_cur
            is_below_p = p_rsi < self.cur_ind_set_tuple.below_rsi_p
            is_below_pp = pp_rsi < self.cur_ind_set_tuple.below_rsi_pp

            result = is_below_cur & is_below_p & is_below_pp & falling & rising

            if result:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Exception long_live_evaluate -> {e}")
            raise Exception(f"Exception long_live_evaluate -> {e}")

    #######################################################
    #######################################################
    #######################################################
    ##################      short    ######################
    ##################      short    ######################
    ##################      short    ######################
    #######################################################
    #######################################################
    #######################################################

    def short_set_cur_ind_tuple(
        self,
        set_idx: int,
    ):
        pass

    def short_entry_message(
        self,
        bar_index: int,
    ):
        pass

    #######################
    ####### reg BT ########
    ####### reg BT ########
    #######################

    def short_set_entries_exits_array(
        self,
        candles: FootprintCandlesTuple,
    ):
        pass

    ########################
    ####### live BT ########
    ####### live BT ########
    ########################

    def short_live_bt_set_entries_exits_array(
        self,
        candles: FootprintCandlesTuple,
    ):
        pass

    def short_live_bt(
        self,
        bar_index: int,
        beg: int,
        candles: FootprintCandlesTuple,
        end: int,
    ):
        pass

    #####################
    ####### live ########
    ####### live ########
    #####################

    def short_live_evaluate(
        self,
        candles: FootprintCandlesTuple,
    ):
        pass

    #######################################################
    #######################################################
    #######################################################
    ##################      Plot     ######################
    ##################      Plot     ######################
    ##################      Plot     ######################
    #######################################################
    #######################################################
    #######################################################

    def plot_signals(
        self,
        candles: FootprintCandlesTuple,
    ):
        datetimes = candles.candle_open_datetimes

        fig = go.Figure()
        fig.add_scatter(
            x=datetimes,
            y=self.rsi,
            name="RSI",
            line_color="yellow",
        )
        fig.add_scatter(
            x=datetimes,
            y=self.entry_signals,
            mode="markers",
            name="entries",
            marker=dict(
                size=12,
                symbol="circle",
                color="#00F6FF",
                line=dict(
                    width=1,
                    color="DarkSlateGrey",
                ),
            ),
        )
        fig.add_hline(
            y=self.h_line,
            opacity=0.3,
            line_color="red",
        )
        fig.update_layout(
            height=500,
            xaxis_rangeslider_visible=False,
            title=dict(
                x=0.5,
                text=self.chart_title,
                xanchor="center",
                font=dict(
                    size=50,
                ),
            ),
        )
        fig.show()


backtest_settings_tuple = BacktestSettings(
    gains_pct_filter=0,
    qf_filter=0,
)

exchange_settings_tuple = ExchangeSettings(
    asset_tick_step=3,
    leverage_mode=1,
    leverage_tick_step=2,
    limit_fee_pct=0.0003,
    market_fee_pct=0.0006,
    max_asset_size=100.0,
    max_leverage=150.0,
    min_asset_size=0.001,
    min_leverage=1.0,
    mmr_pct=0.004,
    position_mode=3,
    price_tick_step=1,
)


long_static_os_tuple = StaticOrderSettings(
    increase_position_type=IncreasePositionType.RiskPctAccountEntrySize,
    leverage_strategy_type=LeverageStrategyType.Dynamic,
    pg_min_max_sl_bcb="min",
    sl_strategy_type=StopLossStrategyType.SLBasedOnCandleBody,
    sl_to_be_bool=False,
    starting_bar=100,
    starting_equity=1000.0,
    static_leverage=None,
    tp_fee_type="limit",
    tp_strategy_type=TakeProfitStrategyType.RiskReward,
    trail_sl_bool=True,
    z_or_e_type=None,
)

long_og_dos_tuple = DynamicOrderSettings(
    account_pct_risk_per_trade=np.array([10]),
    max_trades=np.array([4, 6, 8]),
    risk_reward=np.array([5, 8, 10, 12]),
    sl_based_on_add_pct=np.array([0.3, 0.5, 0.7]),
    sl_based_on_lookback=np.array([50]),
    sl_bcb_type=np.array([CandleBodyType.Low]),
    sl_to_be_cb_type=np.array([CandleBodyType.Nothing]),
    sl_to_be_when_pct=np.array([0]),
    trail_sl_bcb_type=np.array([CandleBodyType.Low]),
    trail_sl_by_pct=np.array([2, 3, 4]),
    trail_sl_when_pct=np.array([2, 3, 4]),
)

rsi_rising_falling_long_strat = RSIRisingFalling(
    long_short="long",
    shuffle_bool=True,
    rsi_length=np.array([15, 25, 35]),
    below_rsi_cur=np.array([30, 40, 60]),
    below_rsi_p=np.array([30, 40, 50]),
    below_rsi_pp=np.array([30, 40, 50]),
)
