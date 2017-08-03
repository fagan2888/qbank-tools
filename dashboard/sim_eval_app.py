from bokeh.models import Div, Slider, Select, CheckboxGroup, CustomJS
from bokeh.models.widgets import Button
from bokeh.layouts import layout, widgetbox

from bokeh.server.server import Server
from bokeh.application.handlers import FunctionHandler
from bokeh.application import Application
from tornado.ioloop import IOLoop

from helpers.common import *
from dashboard.settings import *
import helpers.bokeh_helper as bh

import siman.simeval as simeval
from siman.sims.tfidf_cos import TfidfCosSim
import siman.all_sims as all_sims


# --- constants -----------------------------------------------------------

WIDGET_BOX_WIDTH = 250
CHARTS_WIDTH = PAGE_WIDTH - WIDGET_BOX_WIDTH
DIV_WIDTH = CHARTS_WIDTH // 2 - 20

COL_OPTIONS = [
    'suff_qtext',
    'type',
    'close_seg_text',
    'all_inclusions',
    'all_exclusions',
    'uuid',
    'survey_id',
    'survey_name',
    'form_type',
    'tr_code',
    'notes'
]
SIM_PARAM_REM_STOP = 'remove stopwords'
SIM_PARAM_STEM = 'stemming'
SIM_PARAM_ONLY_ALPHA_NUM = 'only alphanum. chars'
SIM_PARAM_LOWER_CASE = 'lowercase'
SIM_PARAMS = [
    SIM_PARAM_REM_STOP,
    SIM_PARAM_STEM,
    SIM_PARAM_ONLY_ALPHA_NUM,
    SIM_PARAM_LOWER_CASE
]

INIT_HM_SAMPLE_SIZE = 30
INIT_HIST_SAMPLE_SIZE = 100
INIT_SIM = TfidfCosSim
INIT_COLS = ['suff_qtext', 'type']
INIT_SPECTRUM_START = 0
INIT_SPECTRUM_END = 1
INIT_SPECTRUM_BUCKETS = 5
INIT_QUESTIONS_PER_BUCKET = 2
INIT_SPECTRUM_SAMPLE_SIZE = 250



class SimEvalApp:
    def update(self):
        # update parameters
        self.hm_sample_size = self.hm_sample_size_ctrl.value
        self.hist_sample_size = self.hist_sample_size_ctrl.value
        self.cols = [COL_OPTIONS[i] for i in self.analysed_cols_ctrl.active]
        sim_class = all_sims.get_sim_class_by_name(self.sim_ctrl.value)
        self.sim = sim_class(self.cols)

        self.spectrum_start = self.spectrum_start_ctrl.value
        self.spectrum_end = self.spectrum_end_ctrl.value
        self.spectrum_buckets = self.spectrum_buckets_ctrl.value
        self.spectrum_bucket_size = self.spectrum_bucket_size_ctrl.value
        self.spectrum_cs_only = 0 in self.spectrum_cs_only_ctrl.active
        self.spectrum_sample = self.spectrum_spectrum_sample_size_ctrl.value

        # --- Heatmaps -----------------------------------------------------------

        def create_hm(cs_only):
            return simeval.get_sim_heatmap(
                self.df,
                self.sim,
                tooltip_fields=self.cols + ['survey_name', 'uuid'],
                cs_only=cs_only,
                sample_size=self.hm_sample_size,
                width=DIV_WIDTH,
                js_on_event=('tap', CustomJS(code="""open_qcomparison(cb_obj['x'], cb_obj['y'])"""))
            )
        hms = [create_hm(cs_only) for cs_only in [True, False]]
        for i in range(len(hms)):
            self.hm_divs[i].text = bh.get_code(hms[i])

        # --- Histograms -----------------------------------------------------------

        def create_hist(cs_only):
            return simeval.get_sim_hist(
                self.df,
                self.sim,
                cs_only=cs_only,
                sample_size=self.hist_sample_size,
                width=DIV_WIDTH
            )
        hists = [create_hist(cs_only) for cs_only in [True, False]]
        for i in range(len(hists)):
            self.hist_divs[i].text = bh.get_code(hists[i])

        # --- Comp divs -----------------------------------------------------------

        comp_divs = simeval.get_comp_divs(
            self.df,
            self.sim,
            sim_cols=self.cols,
            width=CHARTS_WIDTH,
            start=self.spectrum_start,
            end=self.spectrum_end,
            buckets=self.spectrum_buckets,
            bucket_size=self.spectrum_bucket_size,
            cs_only=self.spectrum_cs_only,
            sample=self.spectrum_sample
        )
        texts = [comp_div.text for comp_div in comp_divs]
        self.comp_div.text = '<br>'.join(texts)

    def __init__(self):
        self.df = load_clean_df()

        # init parameters
        self.hm_sample_size = INIT_HM_SAMPLE_SIZE
        self.hist_sample_size = INIT_HIST_SAMPLE_SIZE
        self.cols = INIT_COLS
        self.sim = INIT_SIM(cols=self.cols)

        # divs holding the charts
        self.hm_divs = [Div(text='', width=DIV_WIDTH) for _ in range(2)]
        self.hist_divs = [Div(text='', width=DIV_WIDTH) for _ in range(2)]
        self.comp_div = Div(text='', width=CHARTS_WIDTH)

        # controls
        self.hm_sample_size_ctrl = Slider(title="Heatmap sample size", value=INIT_HM_SAMPLE_SIZE, start=10, end=100, step=5)
        self.hist_sample_size_ctrl = Slider(title="Histogram sample size", value=INIT_HIST_SAMPLE_SIZE, start=10, end=1000, step=10)
        self.sim_ctrl = Select(title="Similarity metric", options=[all_sims.get_sim_name(s) for s in all_sims.SIMS], value=all_sims.get_sim_name(INIT_SIM))
        self.analysed_cols_ctrl = CheckboxGroup(labels=COL_OPTIONS, active=[COL_OPTIONS.index(c) for c in INIT_COLS])
        self.sim_params = CheckboxGroup(labels=SIM_PARAMS, active=list(range(len(SIM_PARAMS))))

        self.spectrum_start_ctrl = Slider(title="Similarity from", value=INIT_SPECTRUM_START, start=0, end=1, step=0.01)
        self.spectrum_end_ctrl = Slider(title="Similarity to", value=INIT_SPECTRUM_END, start=0, end=1, step=0.01)
        self.spectrum_buckets_ctrl = Slider(title="Number of buckets", value=INIT_SPECTRUM_BUCKETS, start=1, end=20, step=1)
        self.spectrum_bucket_size_ctrl = Slider(title="Questions per bucket", value=INIT_QUESTIONS_PER_BUCKET, start=1, end=10, step=1)
        self.spectrum_cs_only_ctrl = CheckboxGroup(labels=['Cross survey only'], active=[])
        self.spectrum_spectrum_sample_size_ctrl = Slider(title="Sample size", value=INIT_SPECTRUM_SAMPLE_SIZE, start=50, end=5000, step=50)

        self.submit_btn = Button(label="Submit", button_type="success")
        self.submit_btn.on_click(self.update)

        self.update()

    def get_layout(self):
        sizing_mode = 'fixed'

        inputs = widgetbox(
            [
                self.submit_btn,
                Div(text='<hr>'),

                Div(text='<b>Similarity method</b>:<br><i>(Not all params work for all methods)</i>'),
                self.sim_ctrl,
                self.sim_params,
                Div(text='Analysed columns:'),
                self.analysed_cols_ctrl,
                Div(text='<hr>'),

                Div(text='<b>Heatmap</b>:'),
                self.hm_sample_size_ctrl,
                Div(text='<hr>'),

                Div(text='<b>Histogram</b>:'),
                self.hist_sample_size_ctrl,
                Div(text='<hr>'),

                Div(text='<b>Example questions pairs</b>:'),
                self.spectrum_start_ctrl,
                self.spectrum_end_ctrl,
                self.spectrum_buckets_ctrl,
                self.spectrum_bucket_size_ctrl,
                self.spectrum_cs_only_ctrl,
                self.spectrum_spectrum_sample_size_ctrl,
                Div(text='<hr>'),


            ],
            sizing_mode=sizing_mode, responsive=True, width=WIDGET_BOX_WIDTH
        )

        charts = layout([
            [Div(text='<h2>Heatmap of similarities on sample</h2>', width=CHARTS_WIDTH)],
            self.hm_divs,

            [Div(text='<h2>Histogram of similarity scores</h2>', width=CHARTS_WIDTH)],
            self.hist_divs,

            [Div(text='<h2>Example question pairs</h2>', width=CHARTS_WIDTH)],
            [self.comp_div],
        ])

        l = layout([
            [inputs, charts],
            [Div(height=200)]  # some empty space
        ], sizing_mode=sizing_mode)

        return l


def run_app(show=True):
    def modify_doc(doc):
        app = SimEvalApp()

        l = app.get_layout()
        doc.add_root(l)
        doc.title = 'Similarity evaluation dashboard'

    io_loop = IOLoop.current()

    bokeh_app = Application(FunctionHandler(modify_doc))

    server = Server({'/': bokeh_app}, io_loop=io_loop, allow_websocket_origin=["*"], port=SIM_EVAL_PORT, host='*', address='0.0.0.0')
    server.start()

    print('Starting Bokeh application on http://localhost:{}/'.format(SIM_EVAL_PORT))

    if show:
        io_loop.add_callback(server.show, "/")
    io_loop.start()


if __name__ == '__main__':
    run_app()