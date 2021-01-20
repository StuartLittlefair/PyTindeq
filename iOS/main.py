from reel import ReelNode, shader_src, digit_h, digit_w
from tindeq import TindeqProgressor
from repeaters import *
from scene import *
from plotting import Plot
import sound
import ui
import random
import time
import math
import cb
import console
     
    
class CriticalForceTest(Scene):
    """
    A Scene object to run a repeater test.
    
    Once running, the device logs force measurements from tindeq, graphs them
    and offers to save the values to a CSV file for layer analysis
    """
    def setup(self):
        """
        Add components to screen, start searcing for tindeq
        """
        console.set_idle_timer_disabled(True)
        self.started = False
        self.stopped = False
        self.start_time = -5
        
        # status of repeater test
        self._state = IdleRepeaterState
        
        # parameters for test
        self.countdown_time = 5
        self.work_interval = 7
        self.rest_interval = 3
        self.num_intervals = 30
        self.zeropoint = 0
        
        # test y/n?
        self.mode = 'test'
        
        # root node to hold all graphical elements
        self.root = Node(parent=self)
        
        # reels for interval timer
        self.reels = []
        for i in range(2):
            reel = ReelNode(10)
            self.root.add_child(reel)
            self.reels.append(reel)

        # start counter at work interval
        self.reels[0].set_value(self.work_interval)
        # add decimal place for second
        self.dot = LabelNode('.', font=('Avenir Next', digit_h))
        self.root.add_child(self.dot)
        
        # and a light shaded overlay to highlight actual digits
        self.overlay = SpriteNode(size=(max(self.size/3), digit_h + 10))
        self.overlay.shader = Shader(shader_src)
        self.root.add_child(self.overlay)

        # add a msgbox; will show status and current load
        self.background_color = "red"
        msg_font = ('Avenir Next', 30)
        self.msgbox = LabelNode('scanning for device', msg_font, color='white')
        self.cyclebox = LabelNode('', msg_font, color='white')

        self.root.add_child(self.msgbox)
        self.root.add_child(self.cyclebox)                                   
        
        self.plot = Plot(parent=self.root, xsize=0.35, ysize=0.2, position=(0, 0), nticks=5)
        
        # add progressor, with this scene as parent
        self.tindeq = TindeqProgressor(self)
        # start scanning for peripherals
        cb.set_central_delegate(self.tindeq)
        cb.scan_for_peripherals()
        self.did_change_size()
        
        # buffers for data!
        self.times = []
        self.data = []
        
    def did_change_size(self):
        self.root.position = self.size/2
        vert = self.size[0] < self.size[1]
        y = 0 if not vert else self.size[1]/8
        for i in range(len(self.reels)):
            x = -self.size[0]/2 + (2+i) *digit_w
            self.reels[i].position = x, y
        self.dot.position = -self.size[0]/2 + 2.5*digit_w, y
        self.overlay.position = -self.size[0]/3, y
        
        if self.size[0] > self.size[1]:
        	self.msgbox.position = self.size/5
        	self.cyclebox.position = self.size[0]/5, self.size[1]/3
        	self.plot.position = self.size[0]/5, self.size[1]/5
        	self.plot.position = 0, -0.3
        else:
        	y = self.size[1]/3
        	self.msgbox.position = 0, -y
        	self.cyclebox.position = 0, -1.2*y
        	self.plot.position = 0, 0
    
    def log_force_sample(self, tstamp, value):
        self.msgbox.text = '{:.2f} kg'.format(value - self.zeropoint)
        self.times.append(tstamp)
        self.data.append(value - self.zeropoint)
        
    def log_rfd_sample(self, tstamp, value):
        pass
        
    def update(self):
        self._state.update(self)
                
    def touch_began(self, touch):
        self._state.touch_began(self, touch)
            
    def touch_moved(self, touch):
        pass
    
    def touch_ended(self, touch):
        pass
        
    def stop(self):
        console.set_idle_timer_disabled(False)
        if self.tindeq.ready:
            self.tindeq.end_logging_weight()
            self.tindeq.sleep()
        cb.reset()

if __name__ == '__main__':
    run(CriticalForceTest())
    
