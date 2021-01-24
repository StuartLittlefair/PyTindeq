from src.tindeq import TindeqProgressor
import time

import asyncio
import tornado
from bokeh.server.server import Server
from bokeh.application import Application
from bokeh.application.handlers.function import FunctionHandler
from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import row, column
from bokeh.models import Button, Slider, Div


class IdleState:
    bkg = 'orange'

    @staticmethod
    def update(parent):
        parent.div.style['background-color'] = parent.state.bkg
        parent.div.text = '10:00'

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = CountDownState


class CountDownState:
    bkg = 'orange'
    duration = 10

    @staticmethod
    def update(parent):
        # count down timer
        elapsed = time.time() - parent.state_start
        remain = CountDownState.duration - elapsed
        fs = int(10 * (remain - int(remain)))
        secs = int(remain)
        parent.div.text = f"{secs:02d}:{fs:02d}"
        parent.div.style['background-color'] = parent.state.bkg
        if elapsed > CountDownState.duration:
            CountDownState.end(parent)

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = GoState


class GoState:
    bkg = 'green'
    duration = 7

    @staticmethod
    def update(parent):
        # count down timer
        elapsed = time.time() - parent.state_start
        remain = GoState.duration - elapsed
        fs = int(10 * (remain - int(remain)))
        secs = int(remain)
        parent.div.text = f"{secs:02d}:{fs:02d}"
        parent.div.style['background-color'] = parent.state.bkg
        if elapsed > GoState.duration:
            GoState.end(parent)

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = RestState


class RestState:
    bkg = 'red'
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
        parent.div.style['background-color'] = parent.state.bkg
        if elapsed > RestState.duration:
            RestState.end(parent)

    @staticmethod
    def end(parent):
        parent.state_start = time.time()
        parent.state = GoState


class CFT:
    def __init__(self):
        self.x = []
        self.y = []
        self.xnew = []
        self.ynew = []
        self.active = False
        self.duration = 240
        self.state = IdleState

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
        fig = figure(title='Real-time Data', sizing_mode='stretch_both')
        fig.line(x='x', y='y', source=source)
        doc.title = "Tindeq!"
        btn = Button(label='Start Test')
        duration_slider = Slider(start=30, end=300, value=240,
                                 step=5, title="Duration")
        self.div = Div(text='10:00',
                       style={'font-size': '800%', 'color': 'white',
                              'background-color': 'orange',
                              'text-align': 'center'})

        def onclick():
            self.duration = duration_slider.value
            io_loop = tornado.ioloop.IOLoop.current()
            io_loop.add_callback(start_test, self)

        btn.on_click(onclick)
        widgets = column(duration_slider, btn, self.div)
        doc.add_root(row(widgets, fig))
        self.source = source
        doc.add_periodic_callback(self.update, 50)

    def update(self):
        self.state.update(self)
        self.source.stream({'x': self.xnew, 'y': self.ynew})
        self.reset()


async def start_test(cft):
    async with TindeqProgressor(cft) as tindeq:
        await tindeq.soft_tare()
        await asyncio.sleep(5)

        cft.active = True
        cft.state.end(cft)
        await asyncio.sleep(cft.state.duration)

        print('Test starts!')
        cft.state.end(cft)
        await tindeq.start_logging_weight()
        await asyncio.sleep(cft.duration)
        await tindeq.stop_logging_weight()
        await asyncio.sleep(0.5)
        cft.state = IdleState


cft = CFT()
apps = {'/': Application(FunctionHandler(cft.make_document))}
server = Server(apps, port=5000)
server.start()

if __name__ == "__main__":
    tornado.platform.asyncio.AsyncIOMainLoop().install()
    io_loop = tornado.ioloop.IOLoop.current()
    print('Opening Bokeh application on http://localhost:5006/')
    io_loop.add_callback(server.show, "/")
    io_loop.start()
