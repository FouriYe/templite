#coding=utf-8

"""
未实现:
	1、模板继承和包含
    2、自定义标签
    3、自动过滤非法字符
    4、参数过滤
    5、复杂的逻辑，如elif 
    6、多个变量循环
    7、空白符控制
"""

import re

class CodeBuilder(object):
	INDENT_STEP=4
	def __init__(self,indent=0):
		self.code=[]
		self.indent_level=indent
	def indent(self):
		self.indent_level+=self.INDENT_STEP
	def dedent(self):
		self.indent_level-=self.INDENT_STEP
	def add_line(self,line):
		self.code.extend([' '*self.indent_level,line,'\n'])
	def add_section(self):
		section=CodeBuilder(indent=self.indent_level)
		self.code.append(section)
		return section
	def __str__(self):
		"""
		不可直接用''.join(self.code),
		因为code里有其他CodeBuilder对象
		"""
		return ''.join(str(c) for c in self.code)
	def get_globals(self):
		assert self.indent_level==0
		global_namespace={}
		python_resource = str(self)
		exec(python_resource,global_namespace)
		return global_namespace

class Templite(object):
	def __init__(self,text,*contexts):
		"""
		为了使用编译出来的函数尽可能快，
		将上下文中的变量提取到python本地变量中。
		同时在加上前缀'c_'防止命名冲突
		"""
		self.context = {}
		for context in contexts:
			self.context.update(context)
		
		self.all_vars = set()
		self.loop_vars = set()
		
		code = CodeBuilder()
		
		code.add_line("def render_function(context,do_dots):")
		code.indent()
		section = code.add_section()
		code.add_line("result = []")
		code.add_line("append_result = result.append")
		code.add_line("extend_result = result.extend")
		code.add_line("to_str = str")
		
		buffered = []
		def flush_output():
			if len(buffered) == 1:
				code.add_line("append_result(%s)" % buffered[0])
			elif len(buffered) > 1:
				code.add_line("extend_result([%s])" % ", ".join(buffered)) 
			del buffered[:]
		
		opt_stack = []
		
		tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)
		
		for token in tokens:
			if token.startswith('{#'):
				continue
			elif token.startswith('{{'):
				buffered.append("to_str(%s)" % self._expr_code(token[2:-2].strip()))
				'''
				expr = self._expr_code(token[2:-2].strip())
				buffered.append("to_str(%s)" % expr)
				'''
			elif token.startswith('{%'):
				flush_output()
				words = token[2:-2].strip().split()
				if words[0] == 'if':
					if len(words) != 2:
						self._syntax_error("Don't understand if tag",token)
					opt_stack.append('if')
					self._syntax_error("if %s:" % self._expr_code(words[1]))
					code.indent()
				elif words[0] == 'for':
					if len(words) != 4 or words[2] != 'in':
						self._syntax_error("Don't understand for tag",token)
					opt_stack.append('for')
					self._variable(words[1],self.loop_vars)
					code.add_line("for c_%s in %s:" % (words[1],self._expr_code(words[3])))
					code.indent()
				elif words[0].startswith('end'):
					if len(words) != 1:
						self._syntax_error("Don't understand end tag",token)
					end_what = words[0][3:]
					if not opt_stack:
						self._syntax_error("Too many ends",token)
					start_what = opt_stack.pop()
					if start_what != end_what:
						self._syntax_error("Mismatched tag",end_what)
					code.dedent()
				else:
					self._syntax_error("Don't understand tag",words[0])
			else:
				if token:
					"""
					str()返回的字符串可读性好，repr()对python友好，
					得到的字符串通常可以用eval()重新得到该对象（并非所有情况都可以）
					"""
					buffered.append(repr(token))
		
		if opt_stack:
			self._syntax_error("Unmatched  action tag",opt_stack[-1])
		
		flush_output()
		
		for var in self.all_vars - self.loop_vars:
			section.add_line("c_%s = context[%r]" % (var,var))
		
		code.add_line("return ''.join(result)")
		code.dedent()
		self._render_function = code.get_globals()['render_function']
	
	def render(self,context=None):
		render_context = dict(self.context)
		if context:
			render_context.update(context)
		return self._render_function(render_context,self._do_dots)
		
	def _syntax_error(self,msg,thing):
		raise TempliteSyntaxError("%s: %r" % (msg, thing))
		
	def _variable(self,var_name,vars_set):
		if not re.match(r"[_a-zA-Z][_a-zA-Z0-9]*$", var_name):
			self._syntax_error("Not a valid name", var_name)
		vars_set.add(var_name)
		
	def _do_dots(self,value,*dots):
		for dot in dots:
			try:
				value=getattr(value,dot)
			except AttributeError:
				value=value[dot]
			#检查value是否可以调用
			if callable(value):
				value=value()
		return value
	
	def _expr_code(self,expr):
		if "|" in expr:
			pipes = expr.split("|")
			code = self._expr_code(pipes[0])
			for func in pipes[1:]:
				self._variable(func,self.all_vars)
				code = "c_%s(%s)" % (func,code)
		elif "." in expr:
			dots = expr.split(".")
			code = self._expr_code(dots[0])
			args = ", ".join(repr(d) for d in dots[1:])
			code = "do_dots(%s,%s)" % (code,args)
		else:
			self._variable(expr,self.all_vars)
			code="c_%s" % expr
		return code
		
temp = Templite('''
<p>Welcome, {{user_name}}!</p>
<p>Products:</p>
<ul>
{% for product in product_list %}
    <li>{{ product.name }}:
        {{ product.price }}</li>
{% endfor %}
</ul>''')
text = temp.render({'user_name':'Charlie!',
'product_list':[{'name':'Apple','price':'1.00'},
{'name':'Fig','price':'1.50'},
{'name':'Pomegranate','price':'3.25'}]})
