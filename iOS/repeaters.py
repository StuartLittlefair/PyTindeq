import time
import sound
import console
import os
import numpy as np
from analysis import ResultsScene, analyse_data

data_slice = slice(-1024,-1)

# Repeater state classes
class IdleRepeaterState(object):
    @staticmethod
    def update(scn):
        if scn.tindeq.ready:
            scn.msgbox.text = "touch screen to start"
            scn.tindeq.start_logging_weight()
            time.sleep(0.5)

    @staticmethod
    def touch_began(scn, touch):
        """
        Touch means go
        """
        if not scn.tindeq.ready:
            return
        # move to countdown state
        scn.background_color = 'orange'
        scn.zeropoint = np.mean(scn.data)
        scn._state = CountdownRepeaterState
        scn.start_time = time.time()
        

class CountdownRepeaterState(object):
    @staticmethod
    def update(scn):
        # update countdown timer
        elapsed = time.time() - scn.start_time
        remaining = scn.countdown_time - elapsed
        scn.msgbox.text = 'starting in {:.0f}s'.format(remaining)
        
        # time to go?
        if time.time() - scn.start_time > scn.countdown_time:
            # clear buffers
            scn.data = []
            scn.times = []
            scn.start_time = time.time()
            time.sleep(0.5)
            # move to started state
            scn.background_color = '#00d300'
            scn.msgbox.text = ''
            scn._state = RunningRepeaterState
            
        
    @staticmethod
    def touch_began(scn, touch):
        """
        Touch when counting down means abort
        """
        scn.start_time = 0
        scn.background_color = 'red'
        scn._state = IdleRepeaterState
        

class RunningRepeaterState(object):
    @staticmethod
    def update(scn):
        """Do the hard work of counting up and down"""
        total_time = scn.rest_interval + scn.work_interval
        elapsed = time.time() - scn.start_time

        scn.plot.set_xy(scn.times[data_slice], scn.data[data_slice])
        scn.plot.draw()
            
        # have we finished the test?
        if elapsed > scn.num_intervals * (scn.rest_interval + scn.work_interval):
            # we are done!
            scn.background_color = 'red'
            scn.msgbox.text = 'Complete'
            scn.tindeq.end_logging_weight()
            scn._state = StoppedRepeaterState
            return
        
        # otherwise
        cycle_number = scn.num_intervals - elapsed // total_time
        time_in_interval = elapsed % total_time
        if time_in_interval > scn.work_interval:
            status = 'rest'
            value = total_time - time_in_interval
        else:
            status = 'work'
            value = scn.work_interval - time_in_interval

        scn.cyclebox.text = '\n Rep {} / {}'.format(int(scn.num_intervals - cycle_number + 1), scn.num_intervals)
        
        scn.background_color = '#00c600' if status == 'work' else 'red'
        if abs(value % 1) < 0.05:
            if (0.5 <= value < 3.5):
                sound.play_effect('rpg:Chop')
            elif (value < 0.5):
                sound.play_effect('game:Beep')
        scn.reels[1].set_value(value % 1 * 10)
        scn.reels[0].set_value(value // 1)

    @staticmethod
    def touch_began(scn, touch):
        """
        Touch when running means stop
        """
        scn.start_time = 0
        scn.background_color = 'red'
        scn.msgbox.text = 'aborted'
        scn.tindeq.end_logging_weight()
        if scn.mode == 'test':
            scn._state = StoppedRepeaterState
        else:
            scn._state = FinalRepeaterState

class StoppedRepeaterState(object):
    @staticmethod
    def update(scn):
        # do nothing
        pass
        
    @staticmethod
    def touch_began(scn, touch):
        """
        Set to idle and start again (ask for confirmation as will overwrite data)
        """
        np.savetxt('junk.txt', np.column_stack((scn.times, scn.data)))
        msg, img = analyse_data('junk.txt', scn.work_interval, scn.rest_interval)
        print(msg)
        mys = ResultsScene(scn, msg, img)
        scn.present_modal_scene(mys)
        scn._state = FinalRepeaterState
                 
class FinalRepeaterState(object):
    @staticmethod
    def update(scn):
        pass
        
    @staticmethod
    def touch_began(scn, touch):
        scn.background_color = 'red'
        scn._state = IdleRepeaterState
        scn.msgbox.text = 'Press to start' if scn.tindeq.ready else 'scanning for device'
        
