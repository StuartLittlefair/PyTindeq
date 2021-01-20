import scene
import ui

class Plot:
    """
    Contains several shapeNodes for axes, data, grid and label
    """
    def __init__(self, parent, xsize=0.5, ysize=0.2, position=(0.3, 0.3), nticks=10,
                 goal=None):
        self.parent = parent
        self.graph_color = 'white'
        
        self.x_min, self.x_max = (0, 1)
        self.y_min, self.y_max = (0, 1)
        self.xsize, self.ysize = xsize, ysize
        self.position = position
        self.nticks = nticks
        self.xdata = None
        self.ydata = None
        
        self.graph = None
        self.axis = None
        self.ticks = None
        self.goal = goal
        self.labels = []
   
    @property
    def position(self):
        return self._position
        
    @position.setter
    def position(self, value):
        self._position = scene.Point(*value)
    
    def reset(self):
    	self.x_min, self.xmax = (0, 1)
    	self.y_min, self.y_max = (0, 1)
    	
    def set_xy(self, xdata, ydata):
        if len(xdata) == 0:
            return
        self.x_min = min(xdata)
        self.x_max = max(max(xdata), self.x_min+0.001)
        self.y_min = min(ydata)
        self.y_max = max(max(ydata), self.y_min+0.001)
        self.xdata = xdata
        self.ydata = ydata
                
    def clear(self):
        if self.graph is not None:
            self.graph.remove_from_parent()
            self.axis.remove_from_parent()
            self.ticks.remove_from_parent()
            if self.target is not None:
                self.target.remove_from_parent()   
            for label in self.labels:
                label.remove_from_parent()
                
    def add_child(self, child):
        child.position += (self.position[0]*self.parent.scene.size[0], self.position[1]*self.parent.scene.size[1])
        self.parent.add_child(child)
           
    def add(self):
        self.add_child(self.graph)
        self.add_child(self.axis)
        self.add_child(self.ticks)
        if self.target is not None:
            self.add_child(self.target)
        for label in self.labels:
            self.add_child(label)
            
    def draw(self):
        self.clear()
        width, height = self.parent.scene.size
        width *= self.xsize
        height *= self.ysize
        if self.xdata is None:
            return
        kwargs = dict(
            fill_color='clear',
            stroke_color='gray',
            anchor_point=(0, 0)    
        )
        scale_x = width / (self.x_max - self.x_min)
        scale_y = height / (self.y_max - self.y_min)
        step_x_axis = scale_x * (self.x_max - self.x_min)/self.nticks
        step_y_axis = scale_y * (self.y_max - self.y_min)/self.nticks
        
        # draw axes
        axesPath = ui.Path()
        # move to graph (0, 0) and add y-axis
        axesPath.move_to(0, 0)
        axesPath.line_to(0, height-self.ysize)
        kwargs['stroke_color'] = 'black'
        self.axis = scene.ShapeNode(axesPath, **kwargs)
        
        # mark values on y-axis
        yPath = ui.Path()
        def makeLabelNode(i):
            label = '{:.01f}'.format(self.y_min + (self.nticks-i)*(self.y_max - self.y_min)/self.nticks)
            n = scene.LabelNode(label, font=('Avenir Next', 13), 
                                position = (-15, height - step_y_axis * i))
            return n
        
        self.labels = []   
        for i in range(self.nticks + 1):
            yPath.move_to(5, height - step_y_axis*i)
            yPath.line_to(0, height - step_y_axis*i)
            self.labels.append(makeLabelNode(i))
        self.ticks = scene.ShapeNode(yPath, **kwargs)
    
        # data
        x = self.xdata
        y = self.ydata
        dataPath = ui.Path()
        dataPath.move_to(scale_x * (x[0] - self.x_min),
                         height - scale_y * (y[0] - self.y_min))
        for i in range(len(x)):
            draw_x = scale_x * (x[i] - self.x_min)
            draw_y = height - scale_y * (y[i] - self.y_min)
            dataPath.line_to(draw_x, draw_y)
        dataPath.line_width = 2
        kwargs['stroke_color'] = self.graph_color
        self.graph = scene.ShapeNode(dataPath, **kwargs)
        
        # target
        kwargs['stroke_color'] = 'gray'
        if self.goal is not None:
            goalPath = ui.Path()
            goalPath.move_to(scale_x * (x[0] - self.x_min), 
                             height - scale_y * (self.goal - self.y_min))
            goalPath.line_to(scale_x * (x[-1] - self.x_min), 
                             height - scale_y * (self.goal - self.y_min))
            self.target = scene.ShapeNode(goalPath, **kwargs)
        else:
            self.target = None
                        
        self.add()
            
            
        
if __name__ == "__main__":
    import numpy as np
    x = np.linspace(0, 12, 100)
    y = 2*np.sin(x)

    class test(scene.Scene):
        def setup(self):
            self.background_color='red'
            self.xoff = 0
            self.root = scene.Node(parent=self)
            self.p = Plot(parent=self.root, xsize=0.35, ysize=0.2, position=(0.5, 0.1), nticks=3, goal=.0)
            self.p.position = (0.05, 0.5)
        def update(self):
            self.xoff += 0.2
            y = 2 * np.sin(x - self.xoff)
            self.p.set_xy(x, y)
            self.p.draw()
            
    t = test()
    scene.run(t)     
