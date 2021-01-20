from functools import partial
import ui
from scene import Node, LabelNode, Action


if min(ui.get_screen_size()) < 750:
	digit_h = 60
else:
	digit_h = 100
digit_w = digit_h * 0.9

shader_src = '''
#extension GL_EXT_shader_framebuffer_fetch : require
void main() {gl_FragColor = vec4(gl_LastFragData[0].rgb-0.1, 1.0);}
'''


class ReelNode (Node):
	def __init__(self, count=10):
		Node.__init__(self)
		self.count = count
		self.labels = []
		self.container = Node(parent=self)
		font = ('Avenir Next', digit_h)
		for i in range(count * 3):
			label = LabelNode(str(i%count), font=font)
			label.position = 0, -i * digit_h
			self.container.add_child(label)
			self.labels.append(label)
		self.set_value(0)
	
	def set_value(self, value):
		value = min(self.count, max(0, value))
		self.value = value
		y = self.count * digit_h + digit_h * value
		self.container.position = (0, y)
		for label in self.labels:
			label_y = y + label.position.y
			label.alpha = 1.0 - abs(label_y) / (digit_h*5.0)
			label.scale = label.alpha
	
	def animate_to(self, value, d=0.2):
		from_value = self.value
		to_value = value
		def anim(from_value, to_value, node, p):
			node.set_value(from_value + p * (to_value-from_value))
		animation = Action.call(partial(anim, from_value, to_value), d)
		self.run_action(animation)
		

