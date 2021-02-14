# Python scripts to allow custom usage of the Tindeq Progressor from iOS devices and laptops.

The Tindeq Progressor has a fairly simple API, which allows for the creation of custom scripts and tools. In this repository I've provided some custom scripts to perform
critical force tests.

## The critical force test

The "critical power model" is widely used in endurance sports. The basic idea behind the model is there is some power output that is sustainable for long durations; this level is known as the critical power, and is related to an athlete's aerobic fitness. Interestingly, it seems to be the case that athletes also have a constant amount of energy that they can expend above the critical power - a finite battery for work about critical power. This used to be called the "anaerobic work capacity", but is now called W', since it's not clear that it is purely anaerobic.

For more info on the concept - have a look at [this video](https://www.youtube.com/watch?v=86Sw3vOCq9U).

Dave Giles at Derby University, together with the crew at Lattice training have done some work testing how well this model applies to rock climbing, and developed some tests to measure it. You can read their papers [here](https://derby.openrepository.com/bitstream/handle/10545/623485/Giles%20%282019%29%20The%20determination%20of%20finger%20flexor%20critical%20force%20in%20rock%20climbers.pdf?sequence=1&isAllowed=y) and [here](https://www.researchgate.net/profile/Dave_Giles2/publication/343601001_An_all-out_test_to_determine_finger_flexor_critical_force_in_rock_climbers/links/5f339ca8a6fdcccc43c21001/An-all-out-test-to-determine-finger-flexor-critical-force-in-rock-climbers.pdf)

In this repository I've provided code for the "all-out critical force test" described in the second paper. You can use these scripts to do your own critical force testing and measure your aerobic and anaerobic performance, or you can use them as a starting point for writing your own custom apps for the Progressor.

-----------
# Running the scripts

The scripts are written in Python 3.

## Laptops

You will need to install the dependencies, [bleak](https://bleak.readthedocs.io) and [bokeh](https://docs.bokeh.org/en/latest/docs/installation.html).

Then download the scripts in this repository. Click the green "Code" button and select "Download Zip". Once you've downloaded and uncompressed the zip file, you can run the tests by navigating to the "laptop" directory in a terminal. Wake up your progressor and type "python critical_force.py".

## iOS devices.

For iOS devices, the scripts here are designed to be used with the [Pythonista](https://www.google.com/url?sa=t&rct=j&q=&esrc=s&source=web&cd=&cad=rja&uact=8&ved=2ahUKEwji0cnYzenuAhVHPcAKHcEYBQ0QFjAJegQIAxAC&url=https%3A%2F%2Fapps.apple.com%2Fus%2Fapp%2Fpythonista-3%2Fid1085978097&usg=AOvVaw3bRq2p9kAOLiy2adnnJViz) app.

Once you have Pythonista installed, download the code from [this link](https://github.com/StuartLittlefair/PyTindeq/archive/main.zip). The iOS files app can uncompress the zip file. Copy the whole folder to the Pythonista folder in iCloud Drive and you should be able to run the code from inside Pythonista.

