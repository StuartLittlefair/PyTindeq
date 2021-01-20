import matplotlib.pyplot as plt
import numpy as np
from scene import (Scene, Node, LabelNode,
                   SpriteNode, Texture)
from ui import Image
from io import BytesIO


class ResultsScene(Scene):
    def __init__(self, caller, msg, img):
        Scene.__init__(self)
        self.msg = msg
        self.caller = caller
        self.img = SpriteNode(Texture(img))

    def setup(self):
        self.background_color = 'white'
        self.root = Node(parent=self)

        self.img.position = self.size/2
        scaling = max((a/b for a, b in zip(self.size, self.img.size)))
        self.img.scale = scaling * 0.8
        self.root.add_child(self.img)

        msg_font = ('Avenir Next', 25)
        self.lbl = LabelNode(self.msg, msg_font, color='black')
        self.lbl.position = self.size / 3
        self.root.add_child(self.lbl)

    def did_change_size(self):
        self.root.position = self.size/2
        self.img.position = self.size/2
        scaling = max((a/b for a, b in zip(self.size, self.img.size)))
        self.img.scale = scaling * 0.8
        self.lbl.position = self.img.size / 1.9

    def touch_began(self, touch):
        self.caller.dismiss_modal_scene()


def sigma_clipped_stats(data):
    mask = np.ones(data.shape).astype('bool')
    for i in range(5):
        mean = np.mean(data[mask])
        mask = np.fabs(data-mean) < 4 * np.std(data[mask])
    return data[mask].mean(), np.median(data[mask]), data[mask].std()


def get_edges(f, trigger_level=1):
    rising_edges = np.flatnonzero(np.logical_and(f[:-1] < 3, f[1:] > 3))
    falling_edges = np.flatnonzero(np.logical_and(f[:-1] > 3, f[1:] < 3))
    # check limits
    if f[0] > trigger_level:
        rising_edges = np.insert(rising_edges, 0, 0)
    return rising_edges, falling_edges


def measure_mean_loads(t, f, trigger_level=10):
    """
    Split the data into single work intervals, and calculate mean load in that interval
    """
    rising_edges, falling_edges = get_edges(f, trigger_level)
    fmeans = []; durations = []; fmeds = []; tmeans = []; errs = []
    for s, e in zip(rising_edges, falling_edges):
        if e-s < 3.5:
            continue

        elapsed = t[e]-t[s]
        time = t[s:e].mean()
        mean, med, std = sigma_clipped_stats(f[s:e])
        fmeans.append(mean)
        fmeds.append(med)
        durations.append(elapsed)
        tmeans.append(time)
        errs.append(std / np.sqrt(e-s))
    return (np.array(tmeans), np.array(durations), np.array(fmeans),
            np.array(fmeds), np.array(errs))


def analyse_data(fname, load_time, rest_time, interactive=False):
    t, f = np.loadtxt(fname).T
    tmeans, durations, _, fmeans, e_fmeans = measure_mean_loads(t, f)
    print(tmeans, fmeans)
    factor = load_time / (load_time + rest_time)
    load_asymptote = np.nanmean(fmeans[-5:-1])
    e_load_asymptote = np.nanstd(fmeans[-5:-1]) / np.sum(np.isfinite(fmeans[-5:-1]))

    critical_load = load_asymptote * factor
    e_critical_load = critical_load * (e_load_asymptote/load_asymptote)

    used_in_each_interval = (fmeans - critical_load) * load_time - critical_load * rest_time
    used_alternative = (fmeans - critical_load) * durations - critical_load * (load_time+rest_time - durations)
    wprime = np.sum(used_in_each_interval)
    wprime_alt = np.sum(used_alternative)
    remaining = wprime_alt - np.cumsum(used_alternative)

    # force constant
    alpha = np.median((fmeans - load_asymptote)/remaining)

    msg = 'peak load = {:.2f} +/- {:.2f} kg\n'.format(fmeans[0], e_fmeans[0])
    msg += 'critical load = {:.2f} +/- {:.2f} kg\n'.format(critical_load, e_critical_load)
    msg += 'asymptotic load = {:.2f} +/- {:.2f} kg\n'.format(load_asymptote, e_load_asymptote)
    msg += "W'' = {:.0f} J\n".format(9.8 * np.sum(used_in_each_interval))
    msg += "W'' (alt) = {:.0f} J\n".format(9.8 * wprime_alt)
    msg += 'Anaerobic function score = {:.1f}'.format(wprime_alt / critical_load)

    fmax = f.max()
    predicted_force = load_asymptote + remaining * (fmax-load_asymptote) / wprime_alt
    #predicted_force = load_asymptote + alpha * remaining

    plt.rcParams.update({'font.size': 12})
    fig, axis = plt.subplots()
    axis.plot(t, f, alpha=0.5)
    axis.errorbar(tmeans, fmeans, yerr=e_fmeans, fmt='o')
    axis.axhline(critical_load, label='critical load')
    axis.axhline(load_asymptote, label='asymptotic load')
    axis.plot(tmeans, predicted_force, label='predicted max force')
    axis.fill_between(tmeans, load_asymptote, predicted_force, color='g', alpha=0.3, label="W''")
    axis.set_xlabel('Time since start (s)')
    axis.set_ylabel('Load (kg)')
    plt.legend()
    axis.set_ylim(bottom=10)
    if interactive:
        print(msg)
        plt.show()
        return
    b = BytesIO()
    plt.savefig(b)
    plt.close('all')
    img = Image.from_data(b.getvalue())
    return msg, img


if __name__ == '__main__':
    import dialogs
    import warnings
    fn = dialogs.pick_document(
        types=['public.data'])
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        analyse_data(fn, 7, 3, True)
