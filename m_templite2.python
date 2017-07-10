#coding=utf-8

"""
未实现:
	1、模板继承
    2、自定义标签
    3、自动过滤非法字符
    4、参数过滤
    5、多个变量循环
    6、空白符控制
"""

import re
import os
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
	def add_codebuilder(self,code_builder):
		for line in code_builder.code:
			self.code.append(line)
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
		#assert self.indent_level==0
		global_namespace={}
		python_resource = str(self)
		exec(python_resource,global_namespace)
		return global_namespace


class Templite(object):
	def __init__(self,text,indent=0,result_name = 'result',name_suffix = '',template_dir='',encoding = 'utf-8',first=True,contexts=None):
		"""
		为了使用编译出来的函数尽可能快，
		将上下文中的变量提取到python本地变量中。
		同时在加上前缀'c_'防止命名冲突
		"""
		#初始化，参数中first的功能是防止在include的时候c_list = contexts['list']出现key error。
		self.result_name = result_name + '_' + name_suffix
		self.func_name = 'render' + '_' + name_suffix
		self.template_dir=template_dir
		self.encoding = encoding
		self.context = {}
		if contexts:
			for context in contexts:
				self.context.update(context)
		#收集处理中遇到的变量
		self.all_vars = set()
		self.loop_vars = set()
		
		self.code_builder = CodeBuilder(indent)
		
		self.code_builder.add_line("def %s(context,do_dots):"%self.func_name)
		self.code_builder.indent()
		
		#section块会在之后的一个for循环里把上下文环境里的变量存为本地变量提高速度
		section = self.code_builder.add_section()
		self.code_builder.add_line("%s = []"%self.result_name)
		self.append_name = "append_%s"%self.result_name
		self.extend_name = "extend_%s"%self.result_name
		self.code_builder.add_line("%s = %s.append"%(self.append_name,self.result_name))
		self.code_builder.add_line("%s = %s.extend"%(self.extend_name,self.result_name))
		self.code_builder.add_line("to_str = str")
		#缓冲区，只需要在需要模板标签的时候flush_output()一下就可以了，其他时候只需要存到缓冲区里
		buffered = []
		def flush_output():
			if len(buffered) == 1:
				self.code_builder.add_line("%s(%s)" % (self.append_name,buffered[0]))
			elif len(buffered) > 1:
				self.code_builder.add_line("%s([%s])" % (self.extend_name,", ".join(buffered))) 
			del buffered[:]
		
		opt_stack = []
		
		tokens = re.split(r"(?s)({{.*?}}|{%.*?%}|{#.*?#})", text)
		#解析器主循环
		for token in tokens:
			self.parse_tag(token,opt_stack,buffered,flush_output)
		
		if opt_stack:
			self._syntax_error("Unmatched  action tag",opt_stack[-1])
		
		flush_output()
		
		if first == True:
			for var in self.all_vars - self.loop_vars:
				section.add_line("c_%s = context[%r]" % (var,var))
		
		self.code_builder.add_line("return ''.join(%s)"%self.result_name)
		self.code_builder.dedent()
		
	
	def parse_tag(self,token,opt_stack,buffered,flush_output):
		if token.startswith('{#'):
			pass
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
				self.code_builder.add_line("if %s:" % self._expr_code(words[1]))
				self.code_builder.indent()
			elif words[0] == 'for':
				if len(words) != 4 or words[2] != 'in':
					self._syntax_error("Don't understand for tag",token)
				opt_stack.append('for')
				self._variable(words[1],self.loop_vars)
				self.code_builder.add_line("for c_%s in %s:" % (words[1],self._expr_code(words[3])))
				self.code_builder.indent()
			elif words[0] == 'else':
				if not opt_stack:
					self._syntax_error("Too many else",token)
				if opt_stack[-1] != 'if':
					self._syntax_error("Mismatched tag",opt_stack[-1])
				self.code_builder.dedent()
				self.code_builder.add_line("else :")
				self.code_builder.indent()
			elif words[0] == 'elif':
				if len(words) != 2:
					self._syntax_error("Don't understand if tag",token)
				if not opt_stack:
					self._syntax_error("Too many elif",token)
				if opt_stack[-1] != 'if':
					self._syntax_error("Mismatched tag",opt_stack[-1])
				self.code_builder.dedent()
				self.code_builder.add_line("elif %s:"% self._expr_code(words[1]))
				self.code_builder.indent()
			elif words[0] == 'break':
				if not opt_stack:
					self._syntax_error("Break outside loop",token)
				self.code_builder.add_line("break")
			elif words[0].startswith('end'):
				if len(words) != 1:
					self._syntax_error("Don't understand end tag",token)
				end_what = words[0][3:]
				if not opt_stack:
					self._syntax_error("Too many ends",token)
				start_what = opt_stack.pop()
				if start_what != end_what:
					self._syntax_error("Mismatched tag",end_what)
				self.code_builder.dedent()
			elif words[0] == 'include':
				if len(words) != 2:
					self._syntax_error("Don't understand tag",token)
				filename = words[1].strip('"\'')
				included_template = self._parse_another_template_file(filename)
				self.code_builder.add_codebuilder(included_template.code_builder)
				self.code_builder.add_line("%s(%s(context,do_dots))"%(self.append_name,included_template.func_name))
			else:
				self._syntax_error("Don't understand tag",words[0])
		else:
			if token:
				"""
				str()返回的字符串可读性好，repr()对python友好，
				得到的字符串通常可以用eval()重新得到该对象（并非所有情况都可以）
				"""
				buffered.append(repr(token))
				
	def _parse_another_template_file(self,filename):
		template_path=os.path.realpath(os.path.join(self.template_dir,filename))
		with open(template_path,encoding = self.encoding) as fp:
			name_suffix = str(hash(template_path)) #通过hash一个后缀防止命名重复
			template_code = Templite(fp.read(),self.code_builder.indent_level,'result',name_suffix,self.template_dir,self.encoding,False,self.context)
		return template_code
		
	def render(self,context=None):
		self._render_function = self.code_builder.get_globals()['%s' % self.func_name]
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
		
	def get_code(self):
		return self.code_builder.code

		
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
