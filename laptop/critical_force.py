from src.tindeq import TindeqProgressor
from src.analysis import analyse_data
import time

import numpy as np
import asyncio
import tornado
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import row, column
from bokeh.models import Button, Slider, Div, Band, Whisker


class IdleState:
    bkg = "orange"

    @staticmethod
    def update(parent):
        parent.div.style["background-color"] = parent.state.bkg
        parent.div.text = "10:00"

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = CountDownState


class CountDownState:
    bkg = "orange"
    duration = 10

    @staticmethod
    def update(parent):
        # count down timer
        elapsed = time.time() - parent.state_start
        remain = CountDownState.duration - elapsed
        fs = int(10 * (remain - int(remain)))
        secs = int(remain)
        parent.div.text = f"{secs:02d}:{fs:02d}"
        parent.div.style["background-color"] = parent.state.bkg
        if elapsed > CountDownState.duration:
            CountDownState.end(parent)

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = GoState


class GoState:
    bkg = "green"
    duration = 7

    @staticmethod
    def update(parent):
        # count down timer
        elapsed = time.time() - parent.state_start
        remain = GoState.duration - elapsed
        fs = int(10 * (remain - int(remain)))
        secs = int(remain)
        parent.div.text = f"{secs:02d}:{fs:02d}"
        parent.div.style["background-color"] = parent.state.bkg
        if elapsed > GoState.duration:
            GoState.end(parent)

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = RestState


class RestState:
    bkg = "red"
    duration = 3

    @staticmethod
    def update(parent):
        # count up timer
        # count down timer
        elapsed = time.time() - parent.state_start
        remain = RestState.duration - elapsed
        fs = int(10 * (remain - int(remain)))
        secs = int(remain)
        parent.div.text = f"{secs:02d}:{fs:02d}"
        parent.div.style["background-color"] = parent.state.bkg
        if elapsed > RestState.duration:
            RestState.end(parent)

    @staticmethod
    def end(parent):
        if parent.test_done:
            parent.state = IdleState
        else:
            parent.state_start = time.time()
            parent.state = GoState
            parent.reps -= 1


class CFT:
    def __init__(self):
        self.x = []
        self.y = []
        self.xnew = []
        self.ynew = []
        self.active = False
        self.duration = 240
        self.reps = 24
        self.state = IdleState
        self.test_done = False
        self.analysed = False
        self.tindeq = None
        io_loop = tornado.ioloop.IOLoop.current()
        io_loop.add_callback(connect, self)

    def log_force_sample(self, time, weight):
        if self.active:
            self.xnew.append(time)
            self.ynew.append(weight)
            self.x.append(time)
            self.y.append(weight)

    def reset(self):
        self.xnew, self.ynew = [], []

    def make_document(self, doc):
        source = ColumnDataSource(data=dict(x=[], y=[]))
        fig = figure(title="Real-time Data", sizing_mode="stretch_both")
        fig.line(x="x", y="y", source=source)
        doc.title = "Tindeq CFT"
        self.btn = Button(label="Waiting for Progressor...")
        duration_slider = Slider(start=5, end=30, value=24, step=1, title="Reps")
        self.laps = Div(
            text=f"Rep {0}/{duration_slider.value}",
            style={"font-size": "400%", "color": "black", "text-align": "center"},
        )
        self.div = Div(
            text="10:00",
            style={
                "font-size": "800%",
                "color": "white",
                "background-color": "orange",
                "text-align": "center",
            },
        )
        self.results_div = Div(
            text="",
            sizing_mode="stretch_width",
            style={"font-size": "150%", "color": "black", "text-align": "left"},
        )

        def onclick():
            self.reps = duration_slider.value
            self.duration = self.reps * 10
            io_loop = tornado.ioloop.IOLoop.current()
            io_loop.add_callback(start_test, self)

        self.btn.on_click(onclick)
        widgets = column(duration_slider, self.btn, self.laps, self.div)
        first_row = row(widgets, fig)
        doc.add_root(column(first_row, self.results_div, sizing_mode="stretch_both"))
        self.source = source
        self.fig = fig
        doc.add_periodic_callback(self.update, 50)

    def update(self):
        if self.test_done and not self.analysed:
            self.btn.label = "Test Complete"
            np.savetxt("test.txt", np.column_stack((self.x, self.y)))
            x = np.array(self.x)
            y = np.array(self.y)
            results = analyse_data(x, y, 7, 3)
            (
                tmeans,
                fmeans,
                e_fmeans,
                msg,
                critical_load,
                load_asymptote,
                predicted_force,
            ) = results
            self.results_div.text = msg

            fill_src = ColumnDataSource(
                dict(
                    x=tmeans,
                    upper=predicted_force,
                    lower=load_asymptote * np.ones_like(tmeans),
                )
            )
            self.fig.add_layout(
                Band(
                    base="x",
                    lower="lower",
                    upper="upper",
                    source=fill_src,
                    fill_alpha=0.7,
                )
            )
            self.fig.circle(tmeans, fmeans, color="red", size=5, line_alpha=0)

            esource = ColumnDataSource(
                dict(x=tmeans, upper=fmeans + e_fmeans, lower=fmeans - e_fmeans)
            )
            self.fig.add_layout(
                Whisker(
                    source=esource,
                    base="x",
                    upper="upper",
                    lower="lower",
                    level="overlay",
                )
            )
            self.analysed = True
        else:
            if self.tindeq is not None:
                self.btn.label = "Start Test"
            self.state.update(self)
            self.source.stream({"x": self.xnew, "y": self.ynew})
            nlaps = self.duration // 10
            self.laps.text = f"Rep {1 + nlaps - self.reps}/{nlaps}"
            self.reset()


async def connect(cft):
    tindeq = TindeqProgressor(cft)
    await tindeq.connect()
    cft.tindeq = tindeq
    await cft.tindeq.soft_tare()
    await asyncio.sleep(5)


async def start_test(cft):
    try:

        cft.state.end(cft)
        await cft.tindeq.start_logging_weight()
        await asyncio.sleep(cft.state.duration)

        print("Test starts!")
        cft.state.end(cft)
        cft.active = True
        await asyncio.sleep(cft.duration)
        await cft.tindeq.stop_logging_weight()
        cft.test_done = True
        await asyncio.sleep(0.5)
        cft.state = IdleState
    except Exception as err:
        print(str(err))
    finally:
        await cft.tindeq.disconnect()
        cft.tindeq = None


cft = CFT()
apps = {"/": Application(FunctionHandler(cft.make_document))}
server = Server(apps, port=5006)
server.start()

if __name__ == "__main__":
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    io_loop = tornado.ioloop.IOLoop.current()
    print("Opening Bokeh application on http://localhost:5006/")
    io_loop.add_callback(server.show, "/")
    io_loop.start()
